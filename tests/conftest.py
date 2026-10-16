from __future__ import annotations

import contextlib
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from falkordb import Graph
from redis.exceptions import ResponseError

from handoff.config import Config
from handoff.graph.connection import connect
from handoff.graph.decisions import add_decision
from handoff.graph.edits import add_edit
from handoff.graph.needs import add_need
from handoff.graph.requests import add_request
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        host="localhost",
        port=6379,
        graph_name=f"test_{uuid.uuid4().hex[:12]}",
        home=tmp_path / "home",
    )


@pytest.fixture
def graph(config: Config) -> Iterator[Graph]:
    g = connect(config)
    yield g
    # ResponseError means the test never wrote anything, so the graph was never created.
    with contextlib.suppress(ResponseError):
        g.delete()


@pytest.fixture
def ready(graph: Graph) -> Graph:
    """A graph with the schema applied and one frontend session, `s1`."""
    ensure_schema(graph)
    upsert_session(graph, session_id="s1", role="frontend", cwd="/w", at=1000)
    return graph


@pytest.fixture
def two_sessions(graph: Graph) -> Graph:
    """Frontend made two requests (the first with a decision and a need); backend made one."""
    ensure_schema(graph)
    upsert_session(graph, session_id="fe", role="frontend", cwd="/w", at=100)
    upsert_session(graph, session_id="be", role="backend", cwd="/w", at=200)
    add_request(graph, session_id="fe", request_id="p1", text="show avatar", at=110)
    add_edit(
        graph,
        request_id="p1",
        edit_id="e1",
        tool="Edit",
        path="Card.tsx",
        summary="+avatar",
        at=111,
    )
    add_decision(
        graph,
        request_id="p1",
        decision_id="d1",
        text="read avatarUrl",
        reason="server owns urls",
        topic="profile",
        at=112,
    )
    add_need(
        graph, request_id="p1", need_id="n1", text="return avatarUrl", for_role="backend", at=113
    )
    add_request(graph, session_id="fe", request_id="p2", text="tidy styles", at=120)
    add_edit(
        graph, request_id="p2", edit_id="e2", tool="Edit", path="Card.tsx", summary="+class", at=121
    )
    add_request(graph, session_id="be", request_id="p3", text="pick up frontend", at=210)
    return graph
