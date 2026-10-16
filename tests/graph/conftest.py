from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session


@pytest.fixture
def ready(graph: Graph) -> Graph:
    """A graph with the schema applied and one frontend session, `s1`."""
    ensure_schema(graph)
    upsert_session(graph, session_id="s1", role="frontend", cwd="/w", at=1000)
    return graph
