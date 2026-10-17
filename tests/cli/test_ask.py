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
