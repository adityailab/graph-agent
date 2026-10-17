"""Which other sessions' work a request read: communication shown as edges."""

from __future__ import annotations

from falkordb import Graph

# Only requests from other sessions count: re-reading your own history is not
# communication. MERGE keeps one edge per pair, stamped with the first reading.
_ADD = (
    "MATCH (me:Session)-[:RECEIVED]->(r:Request {id: $rid}) "
    "UNWIND $ids AS cid "
    "MATCH (other:Session)-[:RECEIVED]->(c:Request {id: cid}) "
    "WHERE other <> me "
    "MERGE (r)-[k:CONSULTED]->(c) "
    "ON CREATE SET k.at = $at"
)


def add_consultations(graph: Graph, *, request_id: str, consulted_ids: list[str], at: int) -> None:
    """Record that `request_id`'s session read the given requests of other sessions."""
    graph.query(_ADD, {"rid": request_id, "ids": consulted_ids, "at": at})
