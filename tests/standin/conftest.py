from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.decisions import add_decision
from handoff.graph.messages import add_message
from handoff.graph.needs import add_need
from handoff.graph.requests import add_request
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session


@pytest.fixture
def history(graph: Graph) -> Graph:
    """Frontend asked for an avatar, decided to allow a missing one, and needs the field;
    backend did unrelated work; deploy sent frontend a message."""
    ensure_schema(graph)
    upsert_session(graph, session_id="fe", role="frontend", cwd="/w", at=100)
    upsert_session(graph, session_id="be", role="backend", cwd="/w", at=100)
    upsert_session(graph, session_id="dp", role="deploy", cwd="/w", at=100)
    add_request(graph, session_id="fe", request_id="p1", text="show the avatar", at=110)
    add_decision(
        graph,
        request_id="p1",
        decision_id="d1",
        text="avatar may be missing",
        reason="show initials when avatarUrl is null",
        topic="profile",
        at=111,
    )
    add_need(
        graph,
        request_id="p1",
        need_id="n1",
        text="return avatarUrl or null",
        for_role="backend",
        at=112,
    )
    add_request(graph, session_id="be", request_id="p2", text="rate limits", at=120)
    add_message(
        graph,
        message_id="m1",
        from_session_id="dp",
        to_role="frontend",
        kind="message",
        text="CDN_URL is set",
        reply_to=None,
        at=130,
    )
    return graph
