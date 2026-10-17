from __future__ import annotations

from pathlib import Path

import pytest
from falkordb import Graph

from handoff.cli.app import main
from handoff.config import Config
from handoff.graph.messages import claim_pending_messages


@pytest.fixture
def in_workspace(tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANDOFF_GRAPH", config.graph_name)
    monkeypatch.setenv("HANDOFF_HOME", str(config.home))
    return tmp_path


def test_once_dry_run_says_what_it_would_send_and_sends_nothing(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["coordinator", "--once", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "would send to backend" in out
    assert "n1" in out
    assert (
        claim_pending_messages(two_sessions, session_id="be", role="backend", since=0, at=10**15)
        == []
    )


def test_once_sends_the_reminder(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["coordinator", "--once"]) == 0
    assert "sent to backend" in capsys.readouterr().out
    texts = [
        m.text
        for m in claim_pending_messages(
            two_sessions, session_id="be", role="backend", since=0, at=10**15
        )
    ]
    assert any("n1" in t for t in texts)


def test_nothing_to_do_says_so(
    ready: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["coordinator", "--once"]) == 0
    assert "Nothing to do" in capsys.readouterr().out
