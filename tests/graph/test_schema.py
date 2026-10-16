from __future__ import annotations

from falkordb import Graph

from handoff.graph.schema import INDEXED, ensure_schema


def _indexed_labels(graph: Graph) -> set[str]:
    return {str(row[0]) for row in graph.list_indices().result_set}


def test_schema_indexes_every_lookup_key(graph: Graph) -> None:
    ensure_schema(graph)
    assert {label for label, _ in INDEXED} <= _indexed_labels(graph)


def test_schema_can_be_applied_twice(graph: Graph) -> None:
    ensure_schema(graph)
    ensure_schema(graph)
    assert {label for label, _ in INDEXED} <= _indexed_labels(graph)
