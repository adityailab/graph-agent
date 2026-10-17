"""Assembling the guide: which graphs, what is in them, what the parts mean, the rules,
and recipes."""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.introspect import graph_stats, index_summary
from handoff.guide.model import KNOWLEDGE_MODEL, WORK_MODEL
from handoff.guide.recipes import RECIPES
from handoff.guide.rules import RULES

_NO_SERVER = (
    "FalkorDB's MCP server is not installed in this project (it needs Node.js for npx; "
    "install Node 18+ and run handoff init again), so Cypher cannot be run from here; "
    "the handoff tools still work."
)


def _how(graph_name: str, falkordb_mcp: bool) -> str:
    if not falkordb_mcp:
        return _NO_SERVER
    return (
        f"Run read-only Cypher yourself with FalkorDB's MCP server: query_graph_readonly, "
        f"graph name `{graph_name}` (or the knowledge graph). It refuses writes."
    )


def _counts(graph: Graph) -> str:
    stats = graph_stats(graph)
    nodes = ", ".join(f"{k}: {v}" for k, v in sorted(stats.labels.items()))
    rels = ", ".join(f"{k}: {v}" for k, v in sorted(stats.relationships.items()))
    return f"Nodes: {nodes or 'none'}.\nRelationships: {rels or 'none'}."


def build_guide(
    graph: Graph, kg: Graph | None, *, graph_name: str, kg_name: str, falkordb_mcp: bool
) -> str:
    """The guide, built from the live graphs."""
    kg_state = "" if kg is not None else " (not built yet: run handoff knowledge)"
    parts = [
        f"Graphs: `{graph_name}` holds the sessions' work; `{kg_name}` holds concepts "
        f"extracted from it{kg_state}.",
        _how(graph_name, falkordb_mcp),
        f"## What is in `{graph_name}` now\n{_counts(graph)}",
        "## The work graph\n" + "\n".join(f"- {p}: {m}" for p, m in WORK_MODEL),
        "## The knowledge graph\n" + "\n".join(f"- {p}: {m}" for p, m in KNOWLEDGE_MODEL),
        "## Indexes\n" + "\n".join(f"- {line}" for line in index_summary(graph)),
        "## FalkorDB 4.22 rules\n" + "\n".join(f"- {rule}" for rule in RULES),
        "## Recipes\n" + "\n".join(f"- {r.name} [{r.graph} graph]:\n  {r.cypher}" for r in RECIPES),
    ]
    return "\n\n".join(parts)
