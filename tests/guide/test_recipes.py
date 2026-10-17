from __future__ import annotations

from falkordb import Graph

from handoff.graph.consultations import add_consultations
from handoff.guide.recipes import RECIPES


def test_every_recipe_for_the_work_graph_runs_read_only(two_sessions: Graph) -> None:
    # Algorithm procedures fail on a relationship type the graph has never had.
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p1"], at=300)
    for recipe in RECIPES:
        if recipe.graph == "work":
            two_sessions.ro_query(recipe.cypher)  # raises if a recipe is broken


def test_every_recipe_for_the_knowledge_graph_runs_read_only(kg: Graph) -> None:
    for recipe in RECIPES:
        if recipe.graph == "kg":
            kg.ro_query(recipe.cypher)


def test_the_fuzzy_search_recipe_finds_a_misspelt_word(two_sessions: Graph) -> None:
    recipe = next(r for r in RECIPES if r.name == "search decisions, typo-tolerant")
    # The decision's reason is "server owns urls"; "urlz" is one typo away from "urls".
    rows = two_sessions.ro_query(recipe.cypher.replace("paise", "urlz")).result_set
    assert rows
