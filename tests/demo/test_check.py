from __future__ import annotations

from falkordb import Graph

from handoff.config import Config
from handoff.demo.check import check_graph
from handoff.graph.consultations import add_consultations
from handoff.graph.decisions import add_decision
from handoff.graph.edits import add_edit
from handoff.graph.messages import add_citations, add_message, claim_pending_messages
from handoff.graph.needs import add_need, resolve_need
from handoff.graph.requests import add_request
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session


def _completed_scenario(graph: Graph) -> None:
    ensure_schema(graph)
    for sid, role in (("fe", "frontend"), ("be", "backend"), ("dp", "deploy")):
        upsert_session(graph, session_id=sid, role=role, cwd="/w", at=1)
    add_request(graph, session_id="fe", request_id="r1", text="Create Checkout.tsx", at=10)
    add_decision(
        graph,
        request_id="r1",
        decision_id="d1",
        text="paise",
        reason="floats",
        topic="money",
        at=11,
    )
    add_need(graph, request_id="r1", need_id="n1", text="int totalPaise", for_role="backend", at=12)
    add_request(graph, session_id="be", request_id="r2", text="Create api/orders.py", at=20)
    add_edit(
        graph, request_id="r2", edit_id="e2", tool="Write", path="api/orders.py", summary="", at=21
    )
    resolve_need(graph, need_id="n1", request_id="r2")
    add_consultations(graph, request_id="r2", consulted_ids=["r1"], at=22)
    add_message(
        graph,
        message_id="m1",
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text="ready",
        reply_to=None,
        at=23,
    )
    claim_pending_messages(graph, session_id="fe", role="frontend", since=0, at=24)
    add_message(
        graph,
        message_id="m2",
        from_session_id="dp",
        to_role="frontend",
        kind="standin_answer",
        text="paise avoid rounding",
        reply_to=None,
        at=30,
    )
    add_citations(graph, message_id="m2", cited_ids=["d1"])


def test_a_complete_scenario_passes(graph: Graph, config: Config) -> None:
    _completed_scenario(graph)
    text, missing = check_graph(config)
    assert missing == []
    assert "Checkout.tsx" in text


def test_each_missing_part_is_named(graph: Graph, config: Config) -> None:
    ensure_schema(graph)
    _, missing = check_graph(config)
    assert "the need, resolved" in missing
    assert "a stand-in answer citing its sources" in missing
