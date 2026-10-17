"""Insights: what FalkorDB's algorithms find important, kept as (:Insight)-[:ABOUT]->()."""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.captions import caption
from handoff.graph.insight_queries import Insight, bridges, collisions, load_bearing, themes
from handoff.graph.introspect import graph_stats
from handoff.graph.records import InsightView


def compute_insights(graph: Graph, kg: Graph | None) -> list[Insight]:
    """Every insight the graphs support now. Each finder runs only when the labels and
    relationships it needs exist, so empty or young graphs give [] rather than errors."""
    stats = graph_stats(graph)
    found: list[Insight] = []
    if stats.relationships.get("TOUCHED"):
        found += collisions(graph)
    if stats.relationships.get("CONSULTED"):
        found += load_bearing(graph) + bridges(graph)
    if kg is not None and graph_stats(kg).relationships.get("RELATES"):
        found += themes(graph, kg)
    return found


def replace_insights(graph: Graph, insights: list[Insight], *, at: int) -> None:
    """Replace the stored insights with these."""
    graph.query("MATCH (i:Insight) DETACH DELETE i")
    for i in insights:
        graph.query(
            "CREATE (i:Insight {kind: $kind, score: $score, text: $text, name: $name, at: $at}) "
            "WITH i MATCH (n) WHERE ID(n) IN $ids CREATE (i)-[:ABOUT]->(n)",
            {
                "kind": i.kind,
                "score": i.score,
                "text": i.text,
                "name": caption(i.text),
                "at": at,
                "ids": list(i.about),
            },
        )


_ORDER = (
    "CASE i.kind WHEN 'collision' THEN 0 WHEN 'load_bearing' THEN 1 WHEN 'bridge' THEN 2 ELSE 3 END"
)


def current_insights(graph: Graph, *, limit: int) -> list[InsightView]:
    """The stored insights, collisions first, then by score."""
    rows = graph.ro_query(
        "MATCH (i:Insight) OPTIONAL MATCH (i)-[:ABOUT]->(n) "
        "WITH i, collect(coalesce(n.path, n.name)) AS about "
        f"RETURN i.kind, i.score, i.text, about ORDER BY {_ORDER}, i.score DESC LIMIT $limit",
        {"limit": limit},
    ).result_set
    return [InsightView(str(k), float(s), str(t), tuple(map(str, a))) for k, s, t, a in rows]


def newest_insight_at(graph: Graph) -> int | None:
    """When insights were last computed, or None if never."""
    rows = graph.ro_query("MATCH (i:Insight) RETURN max(i.at)").result_set
    return int(rows[0][0]) if rows and rows[0][0] is not None else None


def refresh_insights(graph: Graph, kg: Graph | None, *, at: int) -> None:
    """Recompute the insights and store them in place of the old ones."""
    replace_insights(graph, compute_insights(graph, kg), at=at)
