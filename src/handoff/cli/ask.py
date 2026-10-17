"""`handoff ask "question"`: headless Claude Code answers from the graphs, writing its own
read-only Cypher with graph_guide's help. Prints the answer and the Cypher it ran."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from handoff.cli.stream_json import ToolCall, delta_of, parse_stream, step_labels
from handoff.config import Config
from handoff.install import non_default_database
from handoff.mcp_config import falkordb_server_entry, handoff_server_entry
from handoff.models.claude_code import child_environment
from handoff.workspace import workspace_config

ASK_TIMEOUT = 180
ALLOWED_TOOLS = (
    "mcp__handoff__graph_guide",
    "mcp__handoff__handoff",
    "mcp__handoff__search",
    "mcp__handoff__why",
    "mcp__falkordb__query_graph_readonly",
    "mcp__falkordb__get_graph_schema",
    "mcp__falkordb__list_graphs",
)
_PROMPT = (
    "Answer the person's question about this project's work from its graphs. Call "
    "graph_guide first, then run read-only Cypher with query_graph_readonly (the guide names "
    "the graphs); the handoff, search and why tools help too. Answer in at most five plain "
    "sentences and say what the data showed.{conversation} Question: {question}"
)


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("ask", help="ask a question; Claude answers from the graphs")
    p.add_argument("question")
    p.add_argument("--model", default=os.environ.get("HANDOFF_ASK_MODEL", "sonnet"))
    p.set_defaults(run=run)


def write_mcp_config(folder: Path, config: Config, *, bin_dir: Path, falkordb: bool) -> Path:
    """Servers for the headless run: ours as the person, with no knowledge worker."""
    handoff = handoff_server_entry(
        str(bin_dir / "handoff-mcp"), config.graph_name, non_default_database(config)
    )
    handoff["env"].update(
        HANDOFF_ROLE="person",
        HANDOFF_KNOWLEDGE="off",
        HANDOFF_FALKORDB_MCP="on" if falkordb else "off",
        HANDOFF_HOME=str(config.home),
    )
    servers: dict[str, Any] = {"handoff": handoff}
    if falkordb:
        servers["falkordb"] = falkordb_server_entry(config)
    path = folder / "ask-mcp.json"
    path.write_text(json.dumps({"mcpServers": servers}))
    return path


def _conversation(history: Sequence[tuple[str, str]]) -> str:
    """Earlier turns as plain text, so a follow-up like "and who replaced it?" has its subject."""
    if not history:
        return ""
    turns = "\n".join(f"Person: {q}\nYou: {a}" for q, a in history)
    return f"\n\nConversation so far (the question below follows on from it):\n{turns}\n\n"


def ask_command(
    question: str,
    *,
    mcp_config: Path,
    model: str,
    history: Sequence[tuple[str, str]] = (),
    partial_messages: bool = False,
) -> list[str]:
    """The headless Claude Code command: our servers only, no project settings or hooks
    (so the question is not recorded as a session's request), read-only tools only."""
    return [
        "claude",
        "-p",
        _PROMPT.format(question=question, conversation=_conversation(history)),
        "--output-format",
        "stream-json",
        "--verbose",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--mcp-config",
        str(mcp_config),
        "--allowedTools",
        *ALLOWED_TOOLS,
        "--no-session-persistence",
        "--model",
        model,
        *(["--include-partial-messages"] if partial_messages else []),
    ]


def _run_claude(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        argv,
        capture_output=True,
        text=True,
        timeout=ASK_TIMEOUT,
        check=False,
        stdin=subprocess.DEVNULL,
        env=child_environment(),
    )


def _stream_claude(
    argv: list[str], progress: Callable[[str, str], None]
) -> subprocess.CompletedProcess[str]:
    """Like `_run_claude`, but reads the output as it arrives and reports each step."""
    lines: list[str] = []
    timer: threading.Timer | None = None
    proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        stdin=subprocess.DEVNULL,
        env=child_environment(),
    )
    timer = threading.Timer(ASK_TIMEOUT, proc.kill)
    timer.start()
    try:
        assert proc.stdout is not None  # noqa: S101 - PIPE was requested above
        for line in proc.stdout:
            lines.append(line)
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                words = delta_of(event)
                if words:
                    progress(*words)
                for step in step_labels(event):
                    progress("step", step)
        stderr = proc.stderr.read() if proc.stderr else ""
        proc.wait()
    finally:
        timer.cancel()
    if proc.returncode and proc.returncode < 0 and not lines:  # killed by the timer
        raise subprocess.TimeoutExpired(argv, ASK_TIMEOUT)
    return subprocess.CompletedProcess(argv, proc.returncode, "".join(lines), stderr)


def _answer(
    question: str,
    model: str,
    config: Config,
    history: Sequence[tuple[str, str]] = (),
    progress: Callable[[str, str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        falkordb = shutil.which("npx") is not None
        path = write_mcp_config(
            Path(tmp), config, bin_dir=Path(sys.executable).parent, falkordb=falkordb
        )
        argv = ask_command(
            question,
            mcp_config=path,
            model=model,
            history=history,
            partial_messages=progress is not None,
        )
        return _stream_claude(argv, progress) if progress else _run_claude(argv)


def cypher_run(calls: list[ToolCall]) -> list[str]:
    """The distinct Cypher the model ran, in order (models sometimes repeat a query)."""
    queries = [
        str(c.input["query"])
        for c in calls
        if c.name.endswith("query_graph_readonly") and c.input.get("query")
    ]
    return list(dict.fromkeys(queries))


def ask_graph(
    question: str,
    config: Config,
    history: Sequence[tuple[str, str]] = (),
    progress: Callable[[str, str], None] | None = None,
    *,
    model: str | None = None,
) -> tuple[str, list[str]]:
    """The answer and the Cypher it ran. Raises FileNotFoundError (no `claude`),
    subprocess.TimeoutExpired, or LookupError (Claude Code gave no answer)."""
    done = _answer(
        question, model or os.environ.get("HANDOFF_ASK_MODEL", "sonnet"), config, history, progress
    )
    answer, calls = parse_stream(done.stdout.splitlines())
    if not answer:
        reason = (done.stderr or "").strip().splitlines()
        raise LookupError(reason[-1] if reason else "Claude Code gave no answer.")
    return answer, cypher_run(calls)


def run(args: argparse.Namespace) -> int:
    """Ask, then print the answer and each Cypher query run."""
    config = workspace_config(Path.cwd().resolve(), os.environ)
    print("Asking Claude Code (this uses your plan; usually under a minute)...", file=sys.stderr)
    try:
        done = _answer(args.question, args.model, config)
    except FileNotFoundError:
        print(
            "Claude Code (claude) is not installed: see https://claude.com/claude-code.",
            file=sys.stderr,
        )
        return 1
    except subprocess.TimeoutExpired:
        print(f"No answer within {ASK_TIMEOUT} s.", file=sys.stderr)
        return 1
    answer, calls = parse_stream(done.stdout.splitlines())
    if not answer:
        reason = (done.stderr or "").strip().splitlines()
        print(reason[-1] if reason else "Claude Code gave no answer.", file=sys.stderr)
        return 1
    print(answer)
    queries = cypher_run(calls)
    if queries:
        print("\nCypher it ran:")
        print("\n".join(f"  {q}" for q in queries))
    return 0
