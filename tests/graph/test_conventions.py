from __future__ import annotations

from falkordb import Graph

from handoff.graph.conventions import add_convention, conventions_for, retire_convention
from handoff.graph.schema import ensure_schema


def test_a_convention_applies_to_everyone_or_to_one_role(graph: Graph) -> None:
    ensure_schema(graph)
    add_convention(
        graph,
        convention_id="c1",
        text="money in paise",
        reason="no float",
        scope="all",
        author="person",
        at=1,
    )
    add_convention(
        graph,
        convention_id="c2",
        text="tests first",
        reason="catch bugs",
        scope="backend",
        author="person",
        at=2,
    )
    assert [c.text for c in conventions_for(graph, "frontend")] == ["money in paise"]
    assert [c.text for c in conventions_for(graph, "backend")] == ["money in paise", "tests first"]


def test_recording_the_same_convention_twice_keeps_one(graph: Graph) -> None:
    ensure_schema(graph)
    for _ in range(2):
        add_convention(
            graph,
            convention_id="c1",
            text="money in paise",
            reason="r",
            scope="all",
            author="person",
            at=1,
        )
    assert len(conventions_for(graph, "any")) == 1


def test_a_retired_convention_stops_applying(graph: Graph) -> None:
    ensure_schema(graph)
    add_convention(
        graph,
        convention_id="c1",
        text="money in paise",
        reason="r",
        scope="all",
        author="person",
        at=1,
    )
    assert retire_convention(graph, "c1", at=5)
    assert conventions_for(graph, "any") == []
    assert not retire_convention(graph, "missing", at=5)
