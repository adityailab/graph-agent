from __future__ import annotations

from falkordb import Graph


def test_connected_graph_answers_a_query(graph: Graph) -> None:
    assert graph.query("RETURN 1").result_set == [[1]]
