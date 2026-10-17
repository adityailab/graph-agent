from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.conventions import add_convention
from handoff.graph.decisions import add_decision
from handoff.graph.memory_graph import memory_graph
from handoff.graph.timeline import supersede_decision


def _kinds(graph: Graph, kind: str) -> set[str]:
    return {n.kind for n in memory_graph(graph, kind, limit=100).nodes}


def test_episodic_memory_draws_requests_edits_and_files(two_sessions: Graph) -> None:
    assert {"Request", "Edit", "File"} <= _kinds(two_sessions, "episodic")


def test_semantic_memory_draws_decisions_with_their_topic(two_sessions: Graph) -> None:
    view = memory_graph(two_sessions, "semantic", limit=100)
    assert {"Decision", "Topic"} <= {n.kind for n in view.nodes}
    assert "about" in {e.kind.lower() for e in view.edges}


def test_temporal_memory_draws_the_sequence_with_times_and_replacements(
    two_sessions: Graph,
) -> None:
    add_decision(
        two_sessions,
        request_id="p3",
        decision_id="d2",
        text="read avatar_url",
        reason="rename",
        topic="profile",
        at=300,
    )
    supersede_decision(two_sessions, new_id="d2", old_id="d1", at=301)
    view = memory_graph(two_sessions, "temporal", limit=100)
    assert {"Request", "Decision"} <= {n.kind for n in view.nodes}
    assert {"NEXT", "LED_TO", "SUPERSEDES"} <= {e.kind for e in view.edges}
    assert all(n.at > 0 for n in view.nodes)


def test_procedural_memory_joins_each_rule_to_who_it_applies_to(two_sessions: Graph) -> None:
    add_convention(
        two_sessions,
        convention_id="c1",
        text="amounts in paise",
        reason="no floats",
        scope="backend",
        author="person",
        at=300,
    )
    view = memory_graph(two_sessions, "procedural", limit=100)
    rule = next(n for n in view.nodes if n.kind == "Convention")
    assert "amounts in paise" in rule.text
    assert any(e.source == rule.id and e.kind == "applies_to" for e in view.edges)


def test_every_kind_can_be_drawn(two_sessions: Graph) -> None:
    for kind in ("working", "episodic", "semantic", "procedural", "temporal", "social"):
        memory_graph(two_sessions, kind, limit=10)


def test_an_unknown_kind_is_refused(two_sessions: Graph) -> None:
    with pytest.raises(ValueError, match="unknown kind"):
        memory_graph(two_sessions, "dreams", limit=5)
