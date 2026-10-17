from __future__ import annotations

from pathlib import Path

import pytest
from falkordb import Graph

from handoff.cli.app import main
from handoff.config import Config
from handoff.graph.decisions import add_decision
from handoff.graph.timeline import supersede_decision


@pytest.fixture
def in_workspace(tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANDOFF_GRAPH", config.graph_name)
    monkeypatch.setenv("HANDOFF_HOME", str(config.home))
    return tmp_path


def test_a_convention_is_added_listed_and_retired(
    graph: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(["conventions", "add", "money is integer paise", "--why", "floats round wrongly"]) == 0
    )
    assert main(["conventions"]) == 0
    out = capsys.readouterr().out
    assert "money is integer paise" in out
    rule_id = out.split("id ")[1].split(")")[0]
    assert main(["conventions", "retire", rule_id]) == 0
    capsys.readouterr()
    main(["conventions"])
    assert "No conventions" in capsys.readouterr().out


def test_adding_a_convention_needs_a_reason(
    graph: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(["conventions", "add", "a rule"])


def test_the_timeline_shows_a_topics_decisions_and_what_replaced_what(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    add_decision(
        two_sessions,
        request_id="p3",
        decision_id="d2",
        text="urls come from the CDN",
        reason="cheaper",
        topic="profile",
        at=300,
    )
    supersede_decision(two_sessions, new_id="d2", old_id="d1", at=301)
    assert main(["timeline", "profile"]) == 0
    out = capsys.readouterr().out
    assert "replaced by d2" in out
    assert "urls come from the CDN" in out


def test_the_timeline_of_an_unknown_topic_says_so(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["timeline", "nothing"]) == 0
    assert "No decisions recorded about nothing." in capsys.readouterr().out


def test_memory_shows_each_kind_and_what_each_session_holds(
    two_sessions: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["memory", "--hours", "1000000"]) == 0
    out = capsys.readouterr().out
    for kind in ("working", "episodic", "semantic", "procedural", "temporal", "social"):
        assert kind in out
    assert "working on: pick up frontend" in out


def test_memory_without_a_graph_says_so(
    config: Config, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["memory"]) == 0
    assert "No work recorded yet" in capsys.readouterr().out
