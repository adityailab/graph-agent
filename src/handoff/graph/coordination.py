"""What the coordinator looks for, and the record that it already acted."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph


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


def claim_action(graph: Graph, *, key: str, rule: str, text: str, at: int) -> bool:
    """Record that the coordinator acts on `key`. False if it already did, so a subject
    is acted on once."""
    # MERGE on the unique key; `fresh` is set only when this call created the node.
    rows = graph.query(
        "MERGE (a:Action {key: $key}) "
        "ON CREATE SET a.rule = $rule, a.text = $text, a.at = $at, a.name = $name, a.fresh = 1 "
        "WITH a, a.fresh AS fresh REMOVE a.fresh RETURN fresh",
        {"key": key, "rule": rule, "text": text, "at": at, "name": f"{rule}: {text}"[:60]},
    ).result_set
    return bool(rows[0][0] == 1)
