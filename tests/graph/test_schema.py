from __future__ import annotations

import pytest
from falkordb import Graph
from redis.exceptions import ResponseError

from handoff.graph.schema import FULLTEXT, INDEXED, UNIQUE, VECTOR, ensure_schema


def _indexed_labels(graph: Graph) -> set[str]:
    return {str(row[0]) for row in graph.list_indices().result_set}


def test_schema_indexes_every_lookup_key(graph: Graph) -> None:
    ensure_schema(graph)
    assert {label for label, _ in INDEXED} <= _indexed_labels(graph)


def test_schema_can_be_applied_twice(graph: Graph) -> None:
    ensure_schema(graph)
    ensure_schema(graph)
    assert {label for label, _ in INDEXED} <= _indexed_labels(graph)


def _index_types(graph: Graph) -> dict[str, set[str]]:
    """label -> set of index kinds ('RANGE', 'FULLTEXT', 'VECTOR')."""
    found: dict[str, set[str]] = {}
    for row in graph.query("CALL db.indexes() YIELD label, types RETURN label, types").result_set:
        kinds = found.setdefault(str(row[0]), set())
        for types in dict(row[1]).values():
            kinds.update(str(t) for t in types)
    return found


def test_schema_adds_full_text_and_vector_indexes(graph: Graph) -> None:
    ensure_schema(graph)
    ensure_schema(graph)
    kinds = _index_types(graph)
    for label, _ in FULLTEXT:
        assert "FULLTEXT" in kinds[label]
    for label, _ in VECTOR:
        assert "VECTOR" in kinds[label]


def test_unique_ids_are_enforced(graph: Graph) -> None:
    ensure_schema(graph)
    ensure_schema(graph)
    statuses = {
        (str(r[1]), tuple(r[2])): str(r[4]) for r in graph.query("CALL db.constraints()").result_set
    }
    for label, prop in UNIQUE:
        assert statuses[(label, (prop,))] == "OPERATIONAL"
    graph.query("CREATE (:Session {id: 'dup'})")
    with pytest.raises(ResponseError):
        graph.query("CREATE (:Session {id: 'dup'})")


def test_existing_duplicate_ids_are_logged_not_fatal(
    graph: Graph, caplog: pytest.LogCaptureFixture
) -> None:
    graph.query("CREATE (:Session {id: 'dup'}), (:Session {id: 'dup'})")
    ensure_schema(graph)
    ensure_schema(graph)
    assert any("Session.id" in r.getMessage() for r in caplog.records)
