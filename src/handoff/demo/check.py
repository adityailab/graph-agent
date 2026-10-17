"""Did the demo work? What the deploy session's handoff and the graph must show."""

from __future__ import annotations

from falkordb import FalkorDB

from handoff.config import Config, knowledge_graph_name
from handoff.format import render_handoff, select_requests
from handoff.graph.connection import connect
from handoff.graph.history import handoff_requests
from handoff.graph.schema import ensure_schema

EXPECTED_TEXT = {
    "the frontend request": "Checkout.tsx",
    "the frontend decision": "Decided:",
    "the need, resolved": "(resolved, id",
    "the backend request": "api/orders.py",
}
EXPECTED_EDGES = {
    "a message delivered to a session": (
        "MATCH (:Message)-[:DELIVERED_TO]->(:Session) RETURN count(*)"
    ),
    "a stand-in answer citing its sources": (
        "MATCH (:Message {kind: 'standin_answer'})-[:CITES]->() RETURN count(*)"
    ),
    "a request that consulted another session's work": (
        "MATCH (:Request)-[:CONSULTED]->(:Request) RETURN count(*)"
    ),
}


def reset_graphs(config: Config) -> None:
    """Delete the demo's graph, its knowledge graph and GraphRAG's ontology graph."""
    db = FalkorDB(host=config.host, port=config.port)
    kg = knowledge_graph_name(config)
    for name in set(db.list_graphs()) & {config.graph_name, kg, f"{kg}__ontology"}:
        db.select_graph(name).delete()
    ensure_schema(connect(config))


def check_graph(config: Config) -> tuple[str, list[str]]:
    """The handoff as deploy sees it, and the expected parts that are missing. Counts are
    taken before rendering; rendering records nothing (the tool would add CONSULTED)."""
    graph = connect(config)
    missing = [n for n, q in EXPECTED_EDGES.items() if graph.query(q).result_set[0][0] == 0]
    text = render_handoff(select_requests(handoff_requests(graph, role=None, since=0), 10))
    missing += [name for name, needle in EXPECTED_TEXT.items() if needle not in text]
    return text, missing
