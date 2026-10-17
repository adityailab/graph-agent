"""The items inside each kind of memory, for the dashboard to open a card, and the memories
that are relevant to what a role is working on."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from falkordb import Graph

from handoff.graph.conventions import all_conventions
from handoff.graph.memory_view import role_contexts
from handoff.graph.search import decision_hits, fulltext_decisions


@dataclass(frozen=True)
class MemoryItem:
    title: str  # what sort of thing it is, e.g. "request" or "rule · all"
    text: str
    role: str  # who it belongs to ("" when nobody in particular)
    at: int


def _rows(graph: Graph, query: str) -> list[list[Any]]:
    return list(graph.ro_query(query).result_set)


def _working(graph: Graph, since: int) -> list[MemoryItem]:
    return [MemoryItem(c.role, c.working_on, c.role, 0) for c in role_contexts(graph, since=since)]


def _episodic(graph: Graph, since: int) -> list[MemoryItem]:
    requests = _rows(
        graph, "MATCH (s:Session)-[:RECEIVED]->(r:Request) RETURN s.role, r.text, r.at"
    )
    edits = _rows(
        graph,
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:CAUSED]->(e:Edit)-[:TOUCHED]->(f:File) "
        "RETURN s.role, f.path + '  ' + coalesce(e.summary, ''), e.at",
    )
    sent = _rows(graph, "MATCH (s:Session)-[:SENT]->(m:Message) RETURN s.role, m.text, m.at")
    parts = (("request", requests), ("edit", edits), ("message", sent))
    return [MemoryItem(k, str(t), str(r), int(a)) for k, rows in parts for r, t, a in rows]


def _semantic(graph: Graph, since: int) -> list[MemoryItem]:
    rows = _rows(
        graph,
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(d:Decision)-[:ABOUT]->(t:Topic) "
        "RETURN s.role, t.name, d.text, d.reason, d.at",
    )
    return [
        MemoryItem(f"decision · {t}", f"{d}  (why: {why})", str(r), int(a))
        for r, t, d, why, a in rows
    ]


def _procedural(graph: Graph, since: int) -> list[MemoryItem]:
    return [
        MemoryItem(f"rule · {c.scope}", f"{c.text}  (why: {c.reason})", c.author, c.at)
        for c in all_conventions(graph)
    ]


def _temporal(graph: Graph, since: int) -> list[MemoryItem]:
    rows = _rows(
        graph,
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(new:Decision)-[:SUPERSEDES]->"
        "(old:Decision) RETURN s.role, old.text, new.text, new.at",
    )
    return [MemoryItem("replaced", f"{o}  →  now: {n}", str(r), int(a)) for r, o, n, a in rows]


def _social(graph: Graph, since: int) -> list[MemoryItem]:
    sent = _rows(
        graph,
        "MATCH (s:Session)-[:SENT]->(m:Message) RETURN s.role + ' → ' + m.to_role, m.text, "
        "s.role, m.at",
    )
    reads = _rows(
        graph,
        "MATCH (a:Session)-[:RECEIVED]->(:Request)-[k:CONSULTED]->(:Request)"
        "<-[:RECEIVED]-(b:Session) "
        "RETURN a.role + ' read ' + b.role, 'looked at their earlier requests', a.role, k.at",
    )
    return [MemoryItem(str(t), str(x), str(r), int(a)) for t, x, r, a in sent + reads]


_KINDS: dict[str, Callable[[Graph, int], list[MemoryItem]]] = {
    "working": _working,
    "episodic": _episodic,
    "semantic": _semantic,
    "procedural": _procedural,
    "temporal": _temporal,
    "social": _social,
}


def memory_items(graph: Graph, kind: str, *, since: int, limit: int) -> list[MemoryItem]:
    """The newest `limit` items of one kind of memory. Raises ValueError for an unknown kind."""
    if kind not in _KINDS:
        raise ValueError(f"unknown kind of memory: {kind}")
    return sorted(_KINDS[kind](graph, since), key=lambda i: i.at, reverse=True)[:limit]


def relevant_memories(graph: Graph, text: str, *, k: int) -> list[MemoryItem]:
    """Decisions whose words match `text` (what a role is working on), best match first."""
    ids = [i for i, _ in fulltext_decisions(graph, text, k=k)]
    return [
        MemoryItem(f"decision · {h.role}", f"{h.text}  (why: {h.reason})", h.role, 0)
        for h in decision_hits(graph, ids)
    ]
