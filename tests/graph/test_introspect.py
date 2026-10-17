from __future__ import annotations

from falkordb import Graph

from handoff.graph.introspect import graph_stats, index_summary


def test_stats_count_what_is_in_the_graph(two_sessions: Graph) -> None:
    stats = graph_stats(two_sessions)
    assert stats.labels["Request"] == 3
    assert stats.relationships["RECEIVED"] == 3


def test_indexes_are_summarised_by_label(two_sessions: Graph) -> None:
    lines = index_summary(two_sessions)
    decision = next(line for line in lines if line.startswith("Decision:"))
    assert "text full-text" in decision
    assert "embedding vector" in decision
