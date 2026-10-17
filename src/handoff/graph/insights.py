"""Insights: what FalkorDB's algorithms find important, kept as (:Insight)-[:CONCERNS]->().

CONCERNS, not ABOUT: the connection tool walks ABOUT, and an insight linking two roles'
work must never pass for a chain of real work between them.
"""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.captions import caption
from handoff.graph.insight_queries import Insight, bridges, collisions, load_bearing, themes
from handoff.graph.introspect import graph_stats
from handoff.graph.records import InsightView

ALL_KINDS = ("collision", "load_bearing", "bridge", "theme")


def compute_insights(graph: Graph, kg: Graph | None, *, since: int = 0) -> list[Insight]:
    """Every insight the graphs support now (collisions only from edits since `since`).
    Each finder runs only when the labels and relationships it needs exist, so empty or
    young graphs give [] rather than errors."""
    stats = graph_stats(graph)
    found: list[Insight] = []
    if stats.relationships.get("TOUCHED"):
        found += collisions(graph, since=since)
    if stats.relationships.get("CONSULTED"):
        found += load_bearing(graph) + bridges(graph)
    if kg is not None and graph_stats(kg).relationships.get("RELATES"):
        found += themes(graph, kg)
    return found


# One query, so readers never see an empty or doubled set mid-refresh.
_REPLACE = """
OPTIONAL MATCH (old:Insight) WHERE old.kind IN $kinds
DETACH DELETE old
WITH count(*) AS gone
UNWIND $rows AS row
CREATE (i:Insight {kind: row.kind, score: row.score, text: row.text, name: row.name, at: $at})
WITH i, row
MATCH (n) WHERE ID(n) IN row.ids
CREATE (i)-[:CONCERNS]->(n)
"""


def replace_insights(
    graph: Graph, insights: list[Insight], *, at: int, kinds: tuple[str, ...] = ALL_KINDS
) -> None:
    """Replace the stored insights of `kinds` with these; other kinds are kept."""
    rows = [
        {
            "kind": i.kind,
            "score": i.score,
            "text": i.text,
            "name": caption(i.text),
            "ids": list(i.about),
        }
        for i in insights
    ]
    graph.query(_REPLACE, {"kinds": list(kinds), "rows": rows, "at": at})


_ORDER = (
    "CASE i.kind WHEN 'collision' THEN 0 WHEN 'load_bearing' THEN 1 WHEN 'bridge' THEN 2 ELSE 3 END"
)


def current_insights(graph: Graph, *, limit: int) -> list[InsightView]:
    """The stored insights, collisions first, then by score."""
    rows = graph.ro_query(
        "MATCH (i:Insight) OPTIONAL MATCH (i)-[:CONCERNS]->(n) "
        "WITH i, collect(coalesce(n.path, n.name)) AS about "
        f"RETURN i.kind, i.score, i.text, about ORDER BY {_ORDER}, i.score DESC LIMIT $limit",
        {"limit": limit},
    ).result_set
    return [InsightView(str(k), float(s), str(t), tuple(map(str, a))) for k, s, t, a in rows]


def newest_insight_at(graph: Graph) -> int | None:
    """When insights were last computed, or None if never."""
    rows = graph.ro_query("MATCH (i:Insight) RETURN max(i.at)").result_set
    return int(rows[0][0]) if rows and rows[0][0] is not None else None


def refresh_insights(graph: Graph, kg: Graph | None, *, at: int, since: int = 0) -> None:
    """Recompute the insights and store them in place of the old ones. Without the
    knowledge graph, themes cannot be computed, so the stored ones are kept."""
    kinds = ALL_KINDS if kg is not None else tuple(k for k in ALL_KINDS if k != "theme")
    replace_insights(graph, compute_insights(graph, kg, since=since), at=at, kinds=kinds)
