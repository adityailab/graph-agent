"""Temporal memory as it happened: every request, edit, decision, message and replacement of
every session, with its time, so what came first (and what replaced what) can be read off."""

from __future__ import annotations

from typing import Any

from falkordb import Graph

# (what it is, query returning role, text, at)
_EVENTS: tuple[tuple[str, str], ...] = (
    ("request", "MATCH (s:Session)-[:RECEIVED]->(r:Request) RETURN s.role, r.text, r.at"),
    (
        "edit",
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:CAUSED]->(e:Edit)-[:TOUCHED]->(f:File) "
        "RETURN s.role, f.path + '  ' + coalesce(e.summary, ''), e.at",
    ),
    (
        "decision",
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(d:Decision)-[:ABOUT]->(t:Topic) "
        "RETURN s.role, '[' + t.name + '] ' + d.text + '  (why: ' + d.reason + ')', d.at",
    ),
    ("message", "MATCH (s:Session)-[:SENT]->(m:Message) RETURN s.role, m.text, m.at"),
    (
        "replaced",
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(new:Decision)"
        "-[:SUPERSEDES]->(old:Decision) "
        "RETURN s.role, old.text + '  →  now: ' + new.text, new.at",
    ),
    (
        "agrees",
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(:Decision)"
        "-[r:AGREES_WITH]->(other:Decision) "
        "MATCH (o:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(other) "
        "RETURN s.role, 'agrees with ' + o.role + ': ' + other.text, r.at",
    ),
)


def timeline(graph: Graph) -> list[tuple[str, str, str, int]]:
    """(kind, text, role, at) for everything that happened, oldest first."""
    found: list[tuple[str, str, str, int]] = []
    for kind, query in _EVENTS:
        rows: list[list[Any]] = graph.ro_query(query).result_set
        found += [(kind, str(text), str(role), int(at or 0)) for role, text, at in rows]
    return sorted(found, key=lambda e: e[3])


def span_ms(graph: Graph) -> tuple[int, int]:
    """The (earliest, latest) time of any request, decision or message; (0, 0) when none."""
    times = [
        int(at)
        for label in ("Request", "Decision", "Message")
        for at in graph.ro_query(f"MATCH (x:{label}) RETURN min(x.at), max(x.at)").result_set[0]
        if at is not None
    ]
    return (min(times), max(times)) if times else (0, 0)
