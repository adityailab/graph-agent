"""Queries about needs: things one session's request requires from another role."""

from __future__ import annotations

from falkordb import Graph


def add_need(
    graph: Graph, *, request_id: str, need_id: str, text: str, for_role: str, at: int
) -> bool:
    """Record something a request needs from another role. Needs start open."""
    rows = graph.query(
        "MATCH (r:Request {id: $rid}) "
        "MERGE (n:Need {id: $nid}) "
        "ON CREATE SET n.text = $text, n.for_role = $for_role, n.status = 'open', n.at = $at "
        "MERGE (r)-[:RAISED]->(n) "
        "RETURN n.id",
        {"rid": request_id, "nid": need_id, "text": text, "for_role": for_role, "at": at},
    ).result_set
    return bool(rows)


def resolve_need(graph: Graph, *, need_id: str, request_id: str) -> bool:
    """Mark a need resolved by a request, usually one in another session."""
    rows = graph.query(
        "MATCH (n:Need {id: $nid}), (r:Request {id: $rid}) "
        "SET n.status = 'resolved' "
        "MERGE (n)-[:RESOLVED_BY]->(r) "
        "RETURN n.id",
        {"nid": need_id, "rid": request_id},
    ).result_set
    return bool(rows)


def count_open_needs(graph: Graph, role: str) -> int:
    """Count needs addressed to `role` that are still open."""
    rows = graph.ro_query(
        "MATCH (n:Need {for_role: $role, status: 'open'}) RETURN count(n)", {"role": role}
    ).result_set
    return int(rows[0][0])
