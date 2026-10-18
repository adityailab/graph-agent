from __future__ import annotations

from falkordb import Graph

from handoff.graph.context_view import concept_graph, work_graph
from handoff.graph.edits import add_edit
from handoff.graph.requests import add_request


def test_work_graph_has_every_kind_of_node_coloured_by_role(two_sessions: Graph) -> None:
    view = work_graph(two_sessions, limit=200)
    kinds = {n.kind for n in view.nodes}
    assert {"Session", "Request", "Decision", "Need", "Edit", "File"} <= kinds
    roles = {n.text: n.role for n in view.nodes if n.kind in ("Request", "Decision")}
    assert roles["show avatar"] == "frontend"
    assert roles["read avatarUrl"] == "frontend"
    assert roles["pick up frontend"] == "backend"


def test_every_edge_joins_two_nodes_that_are_listed(two_sessions: Graph) -> None:
    view = work_graph(two_sessions, limit=200)
    ids = {n.id for n in view.nodes}
    assert view.edges
    assert all(e.source in ids and e.target in ids for e in view.edges)


def test_a_file_changed_by_two_roles_is_shared(two_sessions: Graph) -> None:
    add_edit(
        two_sessions,
        request_id="p3",
        edit_id="e9",
        tool="Edit",
        path="Card.tsx",
        summary="+x",
        at=215,
    )
    files = {n.text: n.role for n in work_graph(two_sessions, limit=200).nodes if n.kind == "File"}
    assert files["Card.tsx"] == "shared"


def test_the_newest_edges_win_when_there_are_too_many(two_sessions: Graph) -> None:
    add_request(two_sessions, session_id="be", request_id="p4", text="newest", at=900)
    view = work_graph(two_sessions, limit=1)
    assert [n.text for n in view.nodes if n.kind == "Request"] == ["newest"]


def test_concepts_come_with_their_type_and_relations(kg: Graph) -> None:
    kg.query(
        "MATCH (a:__Entity__ {name: 'avatarUrl'}), (u:__Entity__ {name: 'CDN_URL'}) "
        "CREATE (a)-[:RELATES {rel_type: 'USES'}]->(u)"
    )
    view = concept_graph(kg, limit=50)
    assert {(n.text, n.kind) for n in view.nodes} == {
        ("avatarUrl", "Concept"),
        ("CDN_URL", "Technology"),
    }
    assert [e.kind for e in view.edges] == ["USES"]


def test_an_edit_node_is_labelled_by_what_it_changed_not_none(two_sessions: Graph) -> None:
    edits = [n.text for n in work_graph(two_sessions, limit=200).nodes if n.kind == "Edit"]
    assert edits
    assert all("None" not in text and text for text in edits)


def test_a_long_request_is_kept_whole_so_the_page_can_show_all_of_it(two_sessions: Graph) -> None:
    long_text = "read " + "the whole handoff before you start, " * 8
    add_request(two_sessions, session_id="fe", request_id="p9", text=long_text, at=950)
    texts = {n.text for n in work_graph(two_sessions, limit=200).nodes}
    assert " ".join(long_text.split()) in texts


def test_nodes_carry_the_time_they_happened(two_sessions: Graph) -> None:
    view = work_graph(two_sessions, limit=100)
    decision = next(n for n in view.nodes if n.kind == "Decision")
    assert decision.at == 112


def test_a_decision_node_names_its_topic(two_sessions: Graph) -> None:
    view = work_graph(two_sessions, limit=200)
    decision = next(n for n in view.nodes if n.kind == "Decision")
    assert decision.topic == "profile"


def test_a_need_node_says_who_it_asks_and_whether_it_is_open(two_sessions: Graph) -> None:
    view = work_graph(two_sessions, limit=200)
    need = next(n for n in view.nodes if n.kind == "Need")
    assert (need.for_role, need.status) == ("backend", "open")
