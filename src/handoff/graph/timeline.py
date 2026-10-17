"""Temporal memory: how decisions on a subject changed over time, and which still stand."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph


@dataclass(frozen=True)
class TimelineEntry:
    decision_id: str
    role: str
    text: str
    reason: str
    at: int
    replaced_by: str | None  # the id of the decision that replaced this one, if any


_TIMELINE = """
MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(d:Decision)-[:ABOUT]->(:Topic {name: $topic})
OPTIONAL MATCH (n:Decision)-[:SUPERSEDES]->(d)
RETURN d.id, s.role, d.text, d.reason, d.at, n.id
ORDER BY d.at, d.id
"""
_SUPERSEDE = """
MATCH (new:Decision {id: $new}), (old:Decision {id: $old})
MERGE (new)-[r:SUPERSEDES]->(old)
ON CREATE SET r.at = $at
SET old.superseded_at = coalesce(old.superseded_at, $at)
RETURN old.id
"""


def _entries(graph: Graph, topic: str) -> list[TimelineEntry]:
    rows = graph.ro_query(_TIMELINE, {"topic": topic.strip().lower()}).result_set
    return [
        TimelineEntry(str(i), str(role), str(t), str(why), int(at), None if n is None else str(n))
        for i, role, t, why, at, n in rows
    ]


def topic_timeline(graph: Graph, topic: str) -> list[TimelineEntry]:
    """Every decision about `topic`, oldest first, each with what replaced it (if anything)."""
    return _entries(graph, topic)


def current_on_topic(graph: Graph, topic: str, *, excluding: str) -> list[TimelineEntry]:
    """The decisions about `topic` that nothing has replaced, except the one called `excluding`."""
    return [
        e for e in _entries(graph, topic) if e.replaced_by is None and e.decision_id != excluding
    ]


def supersede_decision(graph: Graph, *, new_id: str, old_id: str, at: int) -> bool:
    """Record that decision `new_id` replaces `old_id`. False if either does not exist."""
    return bool(graph.query(_SUPERSEDE, {"new": new_id, "old": old_id, "at": at}).result_set)
