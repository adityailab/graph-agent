from __future__ import annotations

from pathlib import Path

import pytest
from falkordb import Graph

from handoff.cli.app import main
from handoff.config import Config
from handoff.graph.messages import claim_pending_messages
from handoff.graph.sessions import upsert_session
from handoff.ids import person_session_id


@pytest.fixture
def in_workspace(tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANDOFF_GRAPH", config.graph_name)
    return tmp_path


def test_a_session_of_that_role_receives_the_message_from_the_person(
    graph: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    upsert_session(graph, session_id="be", role="backend", cwd=str(in_workspace), at=1)
    assert main(["send", "Backend", "prices are in paise"]) == 0
    assert "Sent to backend." in capsys.readouterr().out
    messages = claim_pending_messages(graph, session_id="be", role="backend", since=0, at=10**15)
    assert [(m.from_role, m.text) for m in messages] == [("person", "prices are in paise")]


def test_a_role_with_no_session_yet_still_gets_it_later(
    graph: Graph, in_workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["send", "deploy", "ship after lunch"]) == 0
    assert "No session has the role deploy yet" in capsys.readouterr().out
    upsert_session(graph, session_id="d1", role="deploy", cwd=str(in_workspace), at=2)
    messages = claim_pending_messages(graph, session_id="d1", role="deploy", since=0, at=10**15)
    assert [m.text for m in messages] == ["ship after lunch"]


def test_one_folder_keeps_one_person_session(graph: Graph, in_workspace: Path) -> None:
    main(["send", "backend", "one"])
    main(["send", "backend", "two"])
    rows = graph.query("MATCH (s:Session {role: 'person'}) RETURN s.id").result_set
    assert rows == [[person_session_id(str(in_workspace.resolve()))]]


def test_secrets_in_the_message_are_redacted(graph: Graph, in_workspace: Path) -> None:
    main(["send", "backend", "use API_KEY='sk-abcdefghijklmnopqrstuvwxyz123'"])
    text = graph.query("MATCH (m:Message) RETURN m.text").result_set[0][0]
    assert "sk-abcdefghij" not in text
