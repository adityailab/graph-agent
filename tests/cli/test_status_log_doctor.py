from __future__ import annotations

import time
from pathlib import Path

import pytest
from falkordb import Graph

from handoff.cli.app import main
from handoff.cli.doctor import findings
from handoff.config import Config
from handoff.install import install


@pytest.fixture
def in_workspace(tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run commands from a folder whose graph is the test graph, at a fixed clock."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANDOFF_GRAPH", config.graph_name)
    monkeypatch.setenv("HANDOFF_HOME", str(config.home))
    monkeypatch.setattr("handoff.cli.status.now_ms", lambda: 300)
    monkeypatch.setattr("handoff.cli.log_cmd.now_ms", lambda: 300)
    return tmp_path


def test_status_lists_sessions_their_work_and_open_needs(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert '"tidy styles"' in out
    assert '"pick up frontend"' in out
    assert "backend: 1 open need" in out
    assert "knowledge worker: not running" in out


def test_status_does_not_create_a_graph(
    config: Config, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from falkordb import FalkorDB

    assert main(["status"]) == 0
    assert "No work recorded yet" in capsys.readouterr().out
    assert config.graph_name not in FalkorDB().list_graphs()


def test_log_shows_one_roles_handoff(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["log", "frontend"]) == 0
    out = capsys.readouterr().out
    assert 'Request 1 (person): "show avatar"' in out
    assert "pick up frontend" not in out
    assert two_sessions.query("MATCH ()-[k:CONSULTED]->() RETURN count(k)").result_set == [[0]]


def test_doctor_on_a_folder_without_handoff(tmp_path: Path, config: Config) -> None:
    found = findings(tmp_path, config)
    assert any("hooks are not installed" in f for f in found)
    assert any(".mcp.json" in f for f in found)


def test_doctor_is_quiet_on_a_healthy_folder(tmp_path: Path, config: Config) -> None:
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    assert findings(tmp_path, config) == []


def test_doctor_reports_an_unreachable_database_and_recent_hook_errors(
    tmp_path: Path, config: Config
) -> None:
    install(tmp_path, bin_dir=Path("/opt/h/bin"), config=config)
    down = Config(config.host, 1, config.graph_name, config.home)
    logs = config.home / "logs"
    logs.mkdir(parents=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    (logs / "hooks.log").write_text(
        f"2020-01-01 00:00:00,000 ERROR handoff.hooks: old trouble\n"
        f"{stamp},000 ERROR handoff.hooks: hook failed\n"
    )
    found = findings(tmp_path, down)
    assert any("does not answer" in f for f in found)
    assert any("hook failed" in f for f in found)
    assert not any("old trouble" in f for f in found)


def test_the_person_is_not_listed_as_a_session_but_their_messages_are_shown(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from handoff.graph.messages import add_message
    from handoff.graph.sessions import upsert_session

    upsert_session(two_sessions, session_id="me", role="person", cwd="/w", at=250)
    add_message(
        two_sessions,
        message_id="m1",
        from_session_id="be",
        to_role="person",
        kind="message",
        text="the endpoint is ready",
        reply_to=None,
        at=260,
    )
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "person" not in out.split("messages for you")[0]
    assert "the endpoint is ready" in out
