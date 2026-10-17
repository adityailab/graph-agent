from __future__ import annotations

from falkordb import Graph

from handoff.guide.build import build_guide


def test_the_guide_names_the_graphs_and_shows_live_counts(two_sessions: Graph) -> None:
    text = build_guide(two_sessions, None, graph_name="shop", kg_name="shop_kg", falkordb_mcp=True)
    assert "`shop`" in text
    assert "`shop_kg`" in text
    assert "Request: 3" in text
    assert "query_graph_readonly" in text
    assert "EXISTS" in text  # the FalkorDB 4.22 rules are there
    assert "CONSULTED" in text  # the model with meanings
    assert "algo.pageRank" in text  # the recipes


def test_without_falkordbs_server_the_guide_says_what_is_missing(two_sessions: Graph) -> None:
    text = build_guide(two_sessions, None, graph_name="g", kg_name="g_kg", falkordb_mcp=False)
    assert "FalkorDB's MCP server is not installed" in text
    assert "not built yet" in text  # no knowledge graph
