"""Finding decisions: FalkorDB full-text and vector indexes, then out through the graph."""

from __future__ import annotations

import re

from falkordb import Graph

from handoff.graph.records import DecisionHit


def _fulltext_query(text: str) -> str:
    """Words only, OR-ed, so the person's text can never be read as query syntax."""
    words = re.findall(r"\w+", text)
    return " | ".join(words)


def fulltext_decisions(graph: Graph, query: str, *, k: int) -> list[tuple[str, float]]:
    """Decision ids matching words of `query` in their text or reason, best first."""
    q = _fulltext_query(query)
    if not q:
        return []
    rows = graph.ro_query(
        "CALL db.idx.fulltext.queryNodes('Decision', $q) YIELD node, score "
        "RETURN node.id, score ORDER BY score DESC LIMIT $k",
        {"q": q, "k": k},
    ).result_set
    return [(str(r[0]), float(r[1])) for r in rows]


def similar_decisions(graph: Graph, vector: list[float], *, k: int) -> list[tuple[str, float]]:
    """Decision ids nearest to `vector`, with cosine distance (lower is closer)."""
    rows = graph.ro_query(
        "CALL db.idx.vector.queryNodes('Decision', 'embedding', $k, vecf32($v)) "
        "YIELD node, score RETURN node.id, score ORDER BY score",
        {"k": k, "v": vector},
    ).result_set
    return [(str(r[0]), float(r[1])) for r in rows]


def decision_hits(graph: Graph, decision_ids: list[str]) -> list[DecisionHit]:
    """Expand decisions through the graph: who decided, for which request, which files,
    and which other roles changed those files. Keeps the order of `decision_ids`."""
    rows = graph.ro_query(
        "UNWIND $ids AS did "
        "MATCH (s:Session)-[:RECEIVED]->(r:Request)-[:LED_TO]->(d:Decision {id: did}) "
        "OPTIONAL MATCH (r)-[:CAUSED]->(:Edit)-[:TOUCHED]->(f:File) "
        "OPTIONAL MATCH (f)<-[:TOUCHED]-(:Edit)<-[:CAUSED]-(:Request)<-[:RECEIVED]-(o:Session) "
        "WHERE o.role <> s.role "
        "RETURN d.id, s.role, r.text, d.text, d.reason, "
        "collect(DISTINCT f.path), collect(DISTINCT o.role)",
        {"ids": decision_ids},
    ).result_set
    by_id = {
        str(r[0]): DecisionHit(
            id=str(r[0]),
            role=str(r[1]),
            request_text=str(r[2]),
            text=str(r[3]),
            reason=str(r[4]),
            files=tuple(sorted(str(p) for p in r[5] if p is not None)),
            related_roles=tuple(sorted(str(o) for o in r[6] if o is not None)),
        )
        for r in rows
    }
    return [by_id[i] for i in decision_ids if i in by_id]
