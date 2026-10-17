"""What is in a graph right now, from FalkorDB's own procedures."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

_KIND = {"RANGE": "range", "FULLTEXT": "full-text", "VECTOR": "vector"}


@dataclass(frozen=True)
class GraphStats:
    labels: dict[str, int]
    relationships: dict[str, int]


def graph_stats(graph: Graph) -> GraphStats:
    """Node counts per label and relationship counts per type (db.meta.stats)."""
    rows = graph.ro_query("CALL db.meta.stats() YIELD labels, relTypes RETURN labels, relTypes")
    labels, rels = rows.result_set[0] if rows.result_set else ({}, {})
    return GraphStats(
        labels={str(k): int(v) for k, v in labels.items()},
        relationships={str(k): int(v) for k, v in rels.items()},
    )


def index_summary(graph: Graph) -> list[str]:
    """One line per indexed label, e.g. 'Decision: id range, text full-text'."""
    rows = graph.ro_query(
        "CALL db.indexes() YIELD label, types, entitytype RETURN label, types, entitytype "
        "ORDER BY label"
    ).result_set
    lines = []
    for label, types, entity in rows:
        fields = ", ".join(
            f"{prop} {_KIND.get(kind, kind.lower())}"
            for prop, kinds in types.items()
            for kind in kinds
        )
        suffix = " (relationship)" if entity == "RELATIONSHIP" else ""
        lines.append(f"{label}{suffix}: {fields}")
    return lines
