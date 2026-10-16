"""Queries about requests: the prompts a person sends to a session."""

from __future__ import annotations

from falkordb import Graph


def add_request(graph: Graph, *, session_id: str, request_id: str, text: str, at: int) -> int:
    """Record a prompt as the session's next request and return its sequence number.

    Calling again with the same request_id changes nothing and returns the same number.
    """
    existing = graph.query(
        "MATCH (r:Request {id: $rid}) RETURN r.seq", {"rid": request_id}
    ).result_set
    if existing:
        return int(existing[0][0])

    previous = graph.query(
        "MATCH (:Session {id: $sid})-[:RECEIVED]->(p:Request) "
        "RETURN p.id, p.seq ORDER BY p.seq DESC LIMIT 1",
        {"sid": session_id},
    ).result_set
    seq = int(previous[0][1]) + 1 if previous else 1

    created = graph.query(
        "MATCH (s:Session {id: $sid}) "
        "CREATE (s)-[:RECEIVED]->(:Request {id: $rid, seq: $seq, text: $text, at: $at})",
        {"sid": session_id, "rid": request_id, "seq": seq, "text": text, "at": at},
    )
    if created.nodes_created == 0:
        raise LookupError(f"no session with id {session_id}")

    if previous:
        graph.query(
            "MATCH (p:Request {id: $pid}), (r:Request {id: $rid}) CREATE (p)-[:NEXT]->(r)",
            {"pid": previous[0][0], "rid": request_id},
        )
    return seq
