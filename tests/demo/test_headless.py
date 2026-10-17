from __future__ import annotations

from pathlib import Path

from handoff.config import Config
from handoff.demo.headless import session_command, session_env


def test_a_session_uses_the_workspace_settings_and_our_tools(tmp_path: Path) -> None:
    argv = session_command("do it", tmp_path, model="haiku")
    assert argv[:3] == ["claude", "-p", "do it"]
    assert argv[argv.index("--setting-sources") + 1] == "local"  # the workspace's hooks
    assert argv[argv.index("--mcp-config") + 1] == str(tmp_path / ".mcp.json")
    assert "mcp__handoff__record_decision" in argv
    assert argv[argv.index("--model") + 1] == "haiku"


def test_the_graph_reaches_sessions_only_through_the_workspace(tmp_path: Path) -> None:
    config = Config("localhost", 6379, "demo", tmp_path)
    env = session_env("backend", config, base={"HANDOFF_GRAPH": "other", "PATH": "/bin"})
    assert env["HANDOFF_ROLE"] == "backend"
    assert "HANDOFF_GRAPH" not in env
    assert env["HANDOFF_KNOWLEDGE"] == "off"
    assert env["HANDOFF_HOME"] == str(tmp_path)
    assert env["PATH"] == "/bin"
