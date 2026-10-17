"""How much the sessions have communicated, counted for the demo's check."""

from __future__ import annotations

from falkordb import Graph

_COUNTS = {
    "delivered_messages": "MATCH (:Message)-[:DELIVERED_TO]->(:Session) RETURN count(*)",
    "cited_answers": ("MATCH (:Message {kind: 'standin_answer'})-[:CITES]->() RETURN count(*)"),
    "consultations": "MATCH (:Request)-[:CONSULTED]->(:Request) RETURN count(*)",
}


def communication_counts(graph: Graph) -> dict[str, int]:
    """Messages delivered, stand-in answers with sources, and reads of other sessions' work."""
    return {name: int(graph.ro_query(q).result_set[0][0]) for name, q in _COUNTS.items()}
