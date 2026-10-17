"""Did the demo work? What the deploy session's handoff and the graph must show."""

from __future__ import annotations

from falkordb import FalkorDB

from handoff.config import Config, knowledge_graph_name
from handoff.format import render_handoff, select_requests
from handoff.graph.communication import communication_counts
from handoff.graph.connection import connect
from handoff.graph.history import handoff_requests
from handoff.graph.schema import ensure_schema

EXPECTED_TEXT = {
    "the frontend request": "Checkout.tsx",
    "the frontend decision": "Decided:",
    "the need, resolved": "(resolved, id",
    "the backend request": "api/orders.py",
}
EXPECTED_COMMUNICATION = {
    "delivered_messages": "a message delivered to a session",
    "cited_answers": "a stand-in answer citing its sources",
    "consultations": "a request that consulted another session's work",
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
    counts = communication_counts(graph)
    missing = [label for key, label in EXPECTED_COMMUNICATION.items() if counts[key] == 0]
    text = render_handoff(select_requests(handoff_requests(graph, role=None, since=0), 10))
    missing += [name for name, needle in EXPECTED_TEXT.items() if needle not in text]
    return text, missing
