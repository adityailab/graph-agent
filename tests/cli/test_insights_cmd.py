from __future__ import annotations

from pathlib import Path

import pytest
from falkordb import Graph

from handoff.cli.app import main
from handoff.config import Config
from handoff.graph.edits import add_edit


@pytest.fixture
def in_workspace(tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANDOFF_GRAPH", config.graph_name)
    return tmp_path


def test_insights_are_computed_and_printed(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    add_edit(
        two_sessions,
        request_id="p3",
        edit_id="e3",
        tool="Edit",
        path="Card.tsx",
        summary="x",
        at=211,
    )
    assert main(["insights"]) == 0
    out = capsys.readouterr().out
    assert "collision" in out
    assert "backend and frontend both changed Card.tsx" in out


def test_a_young_graph_says_there_is_nothing_yet(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["insights"]) == 0
    assert "No insights yet" in capsys.readouterr().out
