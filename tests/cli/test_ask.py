from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from handoff.cli.app import main
from handoff.cli.ask import ALLOWED_TOOLS, ask_command, write_mcp_config
from handoff.config import Config

CAPTURE = Path(__file__).parent / "data" / "ask_stream.jsonl"


def test_the_command_is_read_only_and_ignores_project_hooks(tmp_path: Path) -> None:
    argv = ask_command("why paise?", mcp_config=tmp_path / "m.json", model="sonnet")
    assert argv[:2] == ["claude", "-p"]
    assert "--strict-mcp-config" in argv
    assert argv[argv.index("--setting-sources") + 1] == ""  # no project hooks or settings
    allowed = argv[
        argv.index("--allowedTools") + 1 : argv.index("--allowedTools") + 1 + len(ALLOWED_TOOLS)
    ]
    assert allowed == list(ALLOWED_TOOLS)
    assert not any(t.startswith("mcp__handoff__record") for t in ALLOWED_TOOLS)
    assert "mcp__falkordb__query_graph" not in ALLOWED_TOOLS  # only the read-only variant
    assert "--permission-mode" not in argv


def test_the_server_config_names_the_graph_and_turns_side_effects_off(
    tmp_path: Path, config: Config
) -> None:
    path = write_mcp_config(tmp_path, config, bin_dir=Path("/opt/h/bin"), falkordb=True)
    servers = json.loads(path.read_text())["mcpServers"]
    env = servers["handoff"]["env"]
    assert env["HANDOFF_GRAPH"] == config.graph_name
    assert env["HANDOFF_KNOWLEDGE"] == "off"
    assert env["HANDOFF_FALKORDB_MCP"] == "on"
    assert servers["falkordb"]["env"]["FALKORDB_STRICT_READONLY"] == "true"


def _answer_with(monkeypatch: pytest.MonkeyPatch, outcome: object) -> None:
    def fake(argv: list[str]) -> subprocess.CompletedProcess[str]:
        if isinstance(outcome, BaseException):
            raise outcome
        return subprocess.CompletedProcess(argv, 0, str(outcome), "")

    monkeypatch.setattr("handoff.cli.ask._run_claude", fake)


def test_ask_prints_the_answer_and_the_cypher(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    _answer_with(monkeypatch, CAPTURE.read_text())
    assert main(["ask", "whose work was read most?"]) == 0
    out = capsys.readouterr().out
    assert "frontend" in out
    assert "MATCH (a:Session)" in out


def test_missing_claude_is_one_sentence(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    _answer_with(monkeypatch, FileNotFoundError("claude"))
    assert main(["ask", "q"]) == 1
    assert "Claude Code (claude) is not installed" in capsys.readouterr().err


def test_a_slow_answer_stops_at_the_limit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    _answer_with(monkeypatch, subprocess.TimeoutExpired("claude", 180))
    assert main(["ask", "q"]) == 1
    assert "No answer within 180 s" in capsys.readouterr().err


def test_earlier_turns_go_into_the_prompt_so_a_follow_up_makes_sense(tmp_path: Path) -> None:
    argv = ask_command(
        "and who replaced it?",
        mcp_config=tmp_path / "m.json",
        model="sonnet",
        history=[("which decision was replaced?", "The CI decision.")],
    )
    prompt = argv[2]
    assert "which decision was replaced?" in prompt
    assert "The CI decision." in prompt
    assert prompt.rstrip().endswith("and who replaced it?")


def test_a_first_question_has_no_conversation_section(tmp_path: Path) -> None:
    prompt = ask_command("hi", mcp_config=tmp_path / "m.json", model="sonnet")[2]
    assert "Conversation so far" not in prompt


def _steps() -> list[str]:
    from handoff.cli.stream_json import step_labels

    labels: list[str] = []
    for line in CAPTURE.read_text().splitlines():
        labels.extend(step_labels(json.loads(line)))
    return labels


def test_a_real_run_reads_as_steps_a_person_can_follow() -> None:
    steps = _steps()
    assert steps[0] == "starting Claude Code"
    assert "thinking" in steps
    assert "reading the graph guide" in steps
    assert any(s.startswith("running Cypher: MATCH") for s in steps)
    assert steps[-1] == "writing the answer"


def test_internal_tool_lookups_are_not_shown_as_steps() -> None:
    assert not any("ToolSearch" in s for s in _steps())


def test_a_streamed_run_reports_steps_as_the_output_arrives(tmp_path: Path) -> None:
    import sys

    from handoff.cli.ask import _stream_claude

    script = tmp_path / "fake_claude.py"
    script.write_text(f"import sys\nsys.stdout.write(open({str(CAPTURE)!r}).read())\n")
    steps: list[str] = []
    done = _stream_claude(
        [sys.executable, str(script)],
        lambda kind, text: steps.append(text) if kind == "step" else None,
    )
    assert done.returncode == 0
    assert steps[0] == "starting Claude Code"
    assert steps[-1] == "writing the answer"
    assert '"type": "result"' in done.stdout or '"type":"result"' in done.stdout


def test_partial_events_give_the_words_as_they_are_written() -> None:
    from handoff.cli.stream_json import delta_of

    text = {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "Two rules"},
        },
    }
    thought = {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "thinking_delta", "thinking": "check the guide"},
        },
    }
    assert delta_of(text) == ("text", "Two rules")
    assert delta_of(thought) == ("thought", "check the guide")
    assert delta_of({"type": "assistant"}) is None
    assert delta_of({"type": "stream_event", "event": {"type": "message_start"}}) is None


def test_a_streamed_run_asks_claude_for_partial_messages(tmp_path: Path) -> None:
    argv = ask_command("hi", mcp_config=tmp_path / "m.json", model="sonnet", partial_messages=True)
    assert "--include-partial-messages" in argv
    assert "--include-partial-messages" not in ask_command(
        "hi", mcp_config=tmp_path / "m.json", model="sonnet"
    )
