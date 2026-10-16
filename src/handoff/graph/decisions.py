"""Queries about decisions: choices a session's agent made, and the topics they are about."""

from __future__ import annotations

from falkordb import Graph


def normalise_topic(topic: str) -> str:
    """Return the canonical form of a topic name, so 'Auth ' and 'auth' are one topic."""
    return " ".join(topic.split()).lower()


def add_decision(
    graph: Graph,
    *,
    request_id: str,
    decision_id: str,
    text: str,
    reason: str,
    topic: str,
    at: int,
) -> bool:
    """Record a decision made for a request, and the topic it is about."""
    rows = graph.query(
        "MATCH (r:Request {id: $rid}) "
        "MERGE (d:Decision {id: $did}) "
        "ON CREATE SET d.text = $text, d.reason = $reason, d.at = $at "
        "MERGE (r)-[:LED_TO]->(d) "
        "MERGE (t:Topic {name: $topic}) "
        "MERGE (d)-[:ABOUT]->(t) "
        "RETURN d.id",
        {
            "rid": request_id,
            "did": decision_id,
            "text": text,
            "reason": reason,
            "topic": normalise_topic(topic),
            "at": at,
        },
    ).result_set
    return bool(rows)
