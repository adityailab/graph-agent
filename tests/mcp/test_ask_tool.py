from __future__ import annotations

import json

from handoff.graph.decisions import add_decision
from handoff.graph.messages import claim_pending_messages
from handoff.mcp.ask_tool import ask
from handoff.mcp.context import ToolContext
from handoff.standin.answer import StandinUnavailable


class FakeClient:
    def __init__(self, reply: str | None = None) -> None:
        self.reply = reply

    def complete(self, system: str, user: str) -> str:
        if self.reply is None:
            raise StandinUnavailable("claude is not logged in")
        return self.reply


def _frontend_decided(backend: ToolContext) -> None:
    add_decision(
        backend.graph,
        request_id="p1",
        decision_id="d1",
        text="avatar may be null",
        reason="initials show instead",
        topic="profile",
        at=1_100,
    )


def test_ask_returns_a_labelled_stand_in_answer_with_sources(backend: ToolContext) -> None:
    _frontend_decided(backend)
    client = FakeClient(
        json.dumps({"answer": "Yes, null is fine.", "cited_ids": ["d1"], "found": True})
    )
    reply = ask(backend, "Frontend", "Can avatarUrl be null?", client)
    assert reply.startswith("Stand-in answer for frontend (from its recorded history")
    assert "Yes, null is fine." in reply
    assert "Sources: d1" in reply


def test_real_session_gets_the_question_and_the_stand_in_answer(backend: ToolContext) -> None:
    _frontend_decided(backend)
    client = FakeClient(json.dumps({"answer": "Yes.", "cited_ids": ["d1"], "found": True}))
    ask(backend, "frontend", "Can avatarUrl be null?", client)
    got = claim_pending_messages(backend.graph, session_id="fe", role="frontend", since=0, at=9_000)
    assert [m.kind for m in got] == ["question", "standin_answer"]
    assert got[1].reply_to == got[0].id


def test_stand_in_answer_cites_its_sources_in_the_graph(backend: ToolContext) -> None:
    _frontend_decided(backend)
    client = FakeClient(json.dumps({"answer": "Yes.", "cited_ids": ["d1"], "found": True}))
    ask(backend, "frontend", "Can avatarUrl be null?", client)
    rows = backend.graph.query(
        "MATCH (m:Message {kind: 'standin_answer'})-[:CITES]->(d:Decision) RETURN d.id"
    ).result_set
    assert rows == [["d1"]]


def test_unavailable_stand_in_still_delivers_the_question(backend: ToolContext) -> None:
    reply = ask(backend, "frontend", "Can avatarUrl be null?", FakeClient(None))
    assert "No stand-in answer is available" in reply
    got = claim_pending_messages(backend.graph, session_id="fe", role="frontend", since=0, at=9_000)
    assert [m.kind for m in got] == ["question"]


def test_blank_question_is_refused(backend: ToolContext) -> None:
    assert ask(backend, "frontend", "  ", FakeClient("{}")) == "Not asked: question is empty."
