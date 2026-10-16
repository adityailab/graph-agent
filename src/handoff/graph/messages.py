"""Queries about messages: text one session sends to a role, delivered once per session."""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.records import MessageView

_ADD_MESSAGE = (
    "MATCH (s:Session {id: $sid}) "
    "MERGE (m:Message {id: $mid}) "
    "ON CREATE SET m.kind = $kind, m.text = $text, m.to_role = $to_role, m.at = $at "
    "MERGE (s)-[:SENT]->(m) "
    "WITH m "
    "OPTIONAL MATCH (q:Message {id: $reply_to}) "
    "FOREACH (_ IN CASE WHEN q IS NULL THEN [] ELSE [1] END | MERGE (m)-[:REPLY_TO]->(q)) "
    "RETURN m.id"
)

# One query: finding and marking delivered happen together, so a hook and the waiter
# claiming at the same moment can never both deliver the same message.
_CLAIM = (
    "MATCH (me:Session {id: $sid}) "
    "MATCH (sender:Session)-[:SENT]->(m:Message {to_role: $role}) "
    "WHERE sender.id <> $sid AND m.at >= $since AND NOT (m)-[:DELIVERED_TO]->(me) "
    "OPTIONAL MATCH (m)-[:REPLY_TO]->(q:Message) "
    "CREATE (m)-[:DELIVERED_TO {at: $at}]->(me) "
    "RETURN m.id, m.kind, sender.role, m.text, q.id, m.at "
    "ORDER BY m.at"
)


def add_message(
    graph: Graph,
    *,
    message_id: str,
    from_session_id: str,
    to_role: str,
    kind: str,
    text: str,
    reply_to: str | None,
    at: int,
) -> bool:
    """Record a message from a session to a role. False if the sender is unknown."""
    rows = graph.query(
        _ADD_MESSAGE,
        {
            "sid": from_session_id,
            "mid": message_id,
            "kind": kind,
            "text": text,
            "to_role": to_role,
            "reply_to": reply_to,
            "at": at,
        },
    ).result_set
    return bool(rows)


def claim_pending_messages(
    graph: Graph, *, session_id: str, role: str, since: int, at: int
) -> list[MessageView]:
    """Return messages to `role` this session has not had yet, oldest first, and mark them
    delivered to it. Messages older than `since` and the session's own are skipped."""
    rows = graph.query(
        _CLAIM, {"sid": session_id, "role": role, "since": since, "at": at}
    ).result_set
    return [
        MessageView(
            id=str(r[0]),
            kind=str(r[1]),
            from_role=str(r[2]),
            text=str(r[3]),
            reply_to=None if r[4] is None else str(r[4]),
            at=int(r[5]),
        )
        for r in rows
    ]
