"""The items inside each kind of memory, for the dashboard to open a card, and the memories
that are relevant to what a role is working on."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from falkordb import Graph

from handoff.graph.conventions import all_conventions
from handoff.graph.memory_timeline import timeline
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
    return [MemoryItem(k, text, role, at) for k, text, role, at in timeline(graph)]


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


def memory_items(
    graph: Graph, kind: str, *, since: int, limit: int, oldest_first: bool = False
) -> list[MemoryItem]:
    """`limit` items of one kind of memory, the newest ones (listed newest first, or oldest
    first with `oldest_first`). Raises ValueError for an unknown kind."""
    if kind not in _KINDS:
        raise ValueError(f"unknown kind of memory: {kind}")
    newest = sorted(_KINDS[kind](graph, since), key=lambda i: i.at, reverse=True)[:limit]
    return newest[::-1] if oldest_first else newest


_STILL_STANDING = (
    "MATCH (d:Decision) WHERE d.id IN $ids AND d.superseded_at IS NULL RETURN d.id, d.at"
)


def relevant_memories(graph: Graph, text: str, *, k: int) -> list[MemoryItem]:
    """Decisions in force whose words match `text` (what a role is working on), best first.
    A decision that a later one replaced is not relevant: it is no longer what the team does."""
    ids = [i for i, _ in fulltext_decisions(graph, text, k=k * 2)]
    standing = {
        str(i): int(at or 0) for i, at in graph.ro_query(_STILL_STANDING, {"ids": ids}).result_set
    }
    return [
        MemoryItem(f"decision · {h.role}", f"{h.text}  (why: {h.reason})", h.role, standing[h.id])
        for h in decision_hits(graph, [i for i in ids if i in standing])[:k]
    ]
