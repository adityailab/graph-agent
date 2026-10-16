"""Queries about requests: the prompts a person sends to a session."""

from __future__ import annotations

from falkordb import Graph

# One query, so a replay or a second session writing at the same moment can never
# create a duplicate request or a half-linked one. FalkorDB runs writes to a graph
# one at a time. The NEXT link is added only when the request is new: its seq is
# then exactly one past the previous request's.
_ADD_REQUEST = (
    "MATCH (s:Session {id: $sid}) "
    "OPTIONAL MATCH (s)-[:RECEIVED]->(p:Request) "
    "WITH s, p ORDER BY p.at DESC LIMIT 1 "
    "MERGE (r:Request {id: $rid}) "
    "ON CREATE SET r.seq = coalesce(p.seq, 0) + 1, r.text = $text, r.at = $at "
    "MERGE (s)-[:RECEIVED]->(r) "
    "FOREACH (_ IN CASE WHEN p IS NOT NULL AND r.seq = p.seq + 1 THEN [1] ELSE [] END | "
    "MERGE (p)-[:NEXT]->(r)) "
    "RETURN r.seq"
)


def add_request(graph: Graph, *, session_id: str, request_id: str, text: str, at: int) -> int:
    """Record a prompt as the session's next request and return its sequence number.

    Calling again with the same request_id changes nothing and returns the same number.
    Raises LookupError if the session is unknown.
    """
    rows = graph.query(
        _ADD_REQUEST, {"sid": session_id, "rid": request_id, "text": text, "at": at}
    ).result_set
    if not rows:
        raise LookupError(f"no session with id {session_id}")
    return int(rows[0][0])


def latest_request_id(graph: Graph, session_id: str) -> str | None:
    """Return the id of the session's most recent request by time, if it has one.

    Ordered by time, not seq, so a request replayed late never counts as the latest.
    """
    rows = graph.ro_query(
        "MATCH (:Session {id: $sid})-[:RECEIVED]->(r:Request) "
        "RETURN r.id ORDER BY r.at DESC, r.seq DESC LIMIT 1",
        {"sid": session_id},
    ).result_set
    return str(rows[0][0]) if rows else None


def request_text(graph: Graph, request_id: str) -> str | None:
    """Return what the person asked in this request, if it exists."""
    rows = graph.ro_query(
        "MATCH (r:Request {id: $rid}) RETURN r.text", {"rid": request_id}
    ).result_set
    return str(rows[0][0]) if rows else None
