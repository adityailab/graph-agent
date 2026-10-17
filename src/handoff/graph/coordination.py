"""What the coordinator looks for, and the record that it already acted."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

from handoff.graph.captions import caption


@dataclass(frozen=True)
class StaleNeed:
    id: str
    for_role: str
    raised_by: str
    text: str
    at: int


@dataclass(frozen=True)
class Collision:
    path: str
    first_role: str
    second_role: str


def stale_needs(graph: Graph, *, cutoff: int) -> list[StaleNeed]:
    """Needs still open that were raised at or before `cutoff`, oldest first."""
    rows = graph.ro_query(
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:RAISED]->(n:Need {status: 'open'}) "
        "WHERE n.at <= $cutoff RETURN n.id, n.for_role, s.role, n.text, n.at ORDER BY n.at",
        {"cutoff": cutoff},
    ).result_set
    return [StaleNeed(str(i), str(f), str(r), str(t), int(a)) for i, f, r, t, a in rows]


def recent_collisions(graph: Graph, *, since: int) -> list[Collision]:
    """Files two different roles both changed at or after `since`, one row per role pair."""
    rows = graph.ro_query(
        "MATCH (s1:Session)-[:RECEIVED]->(:Request)-[:CAUSED]->(e1:Edit)-[:TOUCHED]->(f:File), "
        "(f)<-[:TOUCHED]-(e2:Edit)<-[:CAUSED]-(:Request)<-[:RECEIVED]-(s2:Session) "
        "WHERE s1.role < s2.role AND e1.at >= $since AND e2.at >= $since "
        "RETURN DISTINCT f.path, s1.role, s2.role ORDER BY f.path",
        {"since": since},
    ).result_set
    return [Collision(str(p), str(a), str(b)) for p, a, b in rows]


@dataclass(frozen=True)
class SharedTopic:
    topic: str
    first_role: str
    second_role: str


def shared_topics(graph: Graph, *, since: int) -> list[SharedTopic]:
    """Topics on which two roles each recorded a decision, neither since replaced, at or after
    `since`; one row per topic and role pair."""
    rows = graph.ro_query(
        "MATCH (s1:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(d1:Decision)-[:ABOUT]->(t:Topic), "
        "(t)<-[:ABOUT]-(d2:Decision)<-[:LED_TO]-(:Request)<-[:RECEIVED]-(s2:Session) "
        "WHERE s1.role < s2.role AND d1.superseded_at IS NULL AND d2.superseded_at IS NULL "
        "AND d1.at >= $since AND d2.at >= $since "
        "RETURN DISTINCT t.name, s1.role, s2.role ORDER BY t.name",
        {"since": since},
    ).result_set
    return [SharedTopic(str(t), str(a), str(b)) for t, a, b in rows]


def action_taken(graph: Graph, *, key: str) -> bool:
    """True if the coordinator already acted on `key` (read-only, for dry runs)."""
    rows = graph.ro_query("MATCH (a:Action {key: $key}) RETURN count(a)", {"key": key}).result_set
    return bool(rows[0][0])


# One query: the Action is claimed and its messages created together, so a failure cannot
# leave a subject marked as done with nobody told. `fresh` is set only on the call that
# creates the Action (MERGE on a unique key), so two coordinators never both send.
_CLAIM_AND_SEND = """
MERGE (a:Action {key: $key})
ON CREATE SET a.rule = $rule, a.text = $text, a.at = $at, a.name = $name, a.fresh = 1
WITH a, a.fresh AS fresh REMOVE a.fresh
WITH fresh WHERE fresh = 1
MATCH (sender:Session {id: $sender})
UNWIND $messages AS msg
CREATE (m:Message {id: msg.id, kind: $kind, text: $text, to_role: msg.role, at: $at,
                   name: $kind + ': ' + $caption})
CREATE (sender)-[:SENT]->(m)
RETURN count(m)
"""


def claim_and_send(
    graph: Graph,
    *,
    key: str,
    rule: str,
    kind: str,
    text: str,
    at: int,
    sender: str,
    deliveries: list[tuple[str, str]],  # (message id, role) for each recipient
) -> bool:
    """Act on `key` once: record the Action and send one message per recipient. False if
    the coordinator already acted on it."""
    rows = graph.query(
        _CLAIM_AND_SEND,
        {
            "key": key,
            "rule": rule,
            "text": text,
            "at": at,
            "kind": kind,
            "sender": sender,
            "name": f"{rule}: {caption(text)}",
            "caption": caption(text),
            "messages": [{"id": i, "role": r} for i, r in deliveries],
        },
    ).result_set
    return bool(rows and rows[0][0])
