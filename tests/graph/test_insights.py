from __future__ import annotations

from falkordb import Graph

from handoff.graph.consultations import add_consultations
from handoff.graph.edits import add_edit
from handoff.graph.insights import compute_insights, current_insights, replace_insights
from handoff.graph.requests import add_request
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session


def _three_roles(graph: Graph) -> None:
    ensure_schema(graph)
    for sid, role in (("fe", "frontend"), ("be", "backend"), ("dp", "deploy")):
        upsert_session(graph, session_id=sid, role=role, cwd="/w", at=1)
    add_request(graph, session_id="fe", request_id="r-fe", text="build checkout", at=10)
    add_request(graph, session_id="be", request_id="r-be", text="orders api", at=20)
    add_request(graph, session_id="dp", request_id="r-dp", text="ship it", at=30)


def _kinds(graph: Graph) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for insight in compute_insights(graph, None):
        found.setdefault(insight.kind, []).append(insight.text)
    return found


def test_a_file_changed_by_two_roles_is_a_collision(graph: Graph) -> None:
    _three_roles(graph)
    for rid, eid in (("r-fe", "e1"), ("r-be", "e2")):
        add_edit(
            graph,
            request_id=rid,
            edit_id=eid,
            tool="Edit",
            path="docker-compose.yml",
            summary="x",
            at=40,
        )
    collisions = _kinds(graph)["collision"]
    assert len(collisions) == 1
    assert "docker-compose.yml" in collisions[0]
    assert "backend" in collisions[0] and "frontend" in collisions[0]  # noqa: PT018


def test_work_read_by_two_other_roles_is_load_bearing(graph: Graph) -> None:
    _three_roles(graph)
    add_consultations(graph, request_id="r-be", consulted_ids=["r-fe"], at=50)
    add_consultations(graph, request_id="r-dp", consulted_ids=["r-fe"], at=51)
    load_bearing = _kinds(graph)["load_bearing"]
    assert len(load_bearing) == 1
    assert "build checkout" in load_bearing[0]


def test_work_that_read_and_was_read_is_a_bridge(graph: Graph) -> None:
    _three_roles(graph)
    add_consultations(graph, request_id="r-be", consulted_ids=["r-fe"], at=50)
    add_consultations(graph, request_id="r-dp", consulted_ids=["r-be"], at=51)
    bridges = _kinds(graph)["bridge"]
    assert len(bridges) == 1
    assert "orders api" in bridges[0]


def test_concept_clusters_in_the_knowledge_graph_are_themes(graph: Graph, kg: Graph) -> None:
    _three_roles(graph)
    add_request(graph, session_id="be", request_id="p9", text="cdn avatars", at=60)
    kg.query(
        "MATCH (a:__Entity__ {name: 'avatarUrl'}), (u:__Entity__ {name: 'CDN_URL'}) "
        "CREATE (c:__Entity__:Service {name: 'image CDN'}), "
        "(a)-[:RELATES {rel_type: 'SERVED_BY'}]->(c), (c)-[:RELATES {rel_type: 'USES'}]->(u), "
        "(u)-[:RELATES {rel_type: 'PREFIXES'}]->(a)"  # a tight cluster, as real themes are
    )
    themes = [i for i in compute_insights(graph, kg) if i.kind == "theme"]
    assert len(themes) == 1
    assert "avatarUrl" in themes[0].text
    replace_insights(graph, themes, at=70)
    about = graph.query("MATCH (:Insight)-[:ABOUT]->(r:Request) RETURN r.id").result_set
    assert ["p9"] in about  # linked back to the work that mentions the concepts


def test_an_empty_or_tiny_graph_has_no_insights_and_no_errors(graph: Graph) -> None:
    ensure_schema(graph)
    assert compute_insights(graph, None) == []
    _three_roles(graph)
    assert compute_insights(graph, None) == []


def test_replacing_keeps_one_named_set(graph: Graph) -> None:
    _three_roles(graph)
    for rid, eid in (("r-fe", "e1"), ("r-be", "e2")):
        add_edit(graph, request_id=rid, edit_id=eid, tool="Edit", path="a.ts", summary="x", at=40)
    for at in (100, 200):
        replace_insights(graph, compute_insights(graph, None), at=at)
    rows = graph.query("MATCH (i:Insight) RETURN i.kind, i.at, i.name").result_set
    assert len(rows) == 1
    assert rows[0][1] == 200
    assert rows[0][2]
    views = current_insights(graph, limit=5)
    assert views[0].kind == "collision"
    assert "a.ts" in views[0].about
