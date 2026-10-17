from __future__ import annotations

from falkordb import Graph

from handoff.graph.knowledge import (
    describe_items,
    entity_documents,
    find_entities,
    merge_same_name_entities,
)


def test_entities_are_found_by_name(kg: Graph) -> None:
    assert next(e.name for e in find_entities(kg, "avatarUrl", k=5)) == "avatarUrl"


def test_entities_lead_back_to_our_ids(kg: Graph) -> None:
    docs = entity_documents(kg, ["avatarUrl", "CDN_URL", "missing"])
    assert docs == {"avatarUrl": ["d1", "p9"], "CDN_URL": ["p9"]}


def test_our_ids_are_described_with_role_and_kind(backend_with_decision: Graph) -> None:
    refs = describe_items(backend_with_decision, ["d1", "p9", "nope"])
    assert [(r.id, r.kind, r.role) for r in refs] == [
        ("d1", "decision", "frontend"),
        ("p9", "request", "backend"),
    ]


def test_same_named_entities_of_different_types_become_one(kg: Graph) -> None:
    kg.query(
        "MATCH (u:__Entity__ {name: 'CDN_URL'}), (c:Chunk {text: 'b'}) "
        "CREATE (a:__Entity__:Technology {name: 'AvatarUrl ', type: 'Technology', "
        "description: 'the url of a user avatar image'}), "
        "(a)-[:MENTIONED_IN]->(c), (a)-[:RELATES {rel_type: 'SERVED_FROM'}]->(u)"
    )
    assert merge_same_name_entities(kg) == 1
    rows = kg.query(
        "MATCH (e:__Entity__) WHERE toLower(trim(e.name)) = 'avatarurl' "
        "OPTIONAL MATCH (e)-[r:RELATES]->(u) "
        "RETURN count(DISTINCT e), e.description, collect(r.rel_type), "
        "size([(e)-[:MENTIONED_IN]->(c) | c])"
    ).result_set
    assert rows == [[1, "the url of a user avatar image", ["SERVED_FROM"], 2]]


def test_merging_twice_changes_nothing(kg: Graph) -> None:
    assert merge_same_name_entities(kg) == 0


def test_merging_does_not_leave_parallel_edges_and_keeps_every_source(kg: Graph) -> None:
    kg.query(
        "MATCH (u:__Entity__ {name: 'CDN_URL'}) "
        "CREATE (a:__Entity__:Concept {name: 'Orders API', description: 'short'}), "
        "(b:__Entity__:API {name: 'orders api', description: 'a much longer description'}), "
        "(a)-[:RELATES {rel_type: 'RETURNS', source_chunk_ids: ['c1']}]->(u), "
        "(b)-[:RELATES {rel_type: 'RETURNS', source_chunk_ids: ['c2']}]->(u)"
    )
    assert merge_same_name_entities(kg) == 1
    rows = kg.query(
        "MATCH (e:__Entity__ {name: 'orders api'})-[r:RELATES {rel_type: 'RETURNS'}]->"
        "(:__Entity__ {name: 'CDN_URL'}) RETURN count(r), collect(r.source_chunk_ids)"
    ).result_set
    assert rows[0][0] == 1
    assert sorted(rows[0][1][0]) == ["c1", "c2"]


def test_names_that_differ_only_in_case_spacing_or_punctuation_become_one(kg: Graph) -> None:
    kg.query(
        "CREATE (:__Entity__:Component {name: 'ProductList', description: 'the list'}), "
        "(:__Entity__:Component {name: 'product list', description: 'x'}), "
        "(:__Entity__:File {name: 'dist/', description: 'build output'}), "
        "(:__Entity__:File {name: 'dist', description: 'x'}), "
        "(:__Entity__:Concept {name: 'login', description: 'x'}), "
        "(:__Entity__:Concept {name: 'logic', description: 'x'})"
    )
    assert merge_same_name_entities(kg) == 2
    names = {r[0] for r in kg.query("MATCH (e:__Entity__) RETURN e.name").result_set}
    assert {"login", "logic"} <= names  # near, but not the same name
    assert ("ProductList" in names) != ("product list" in names)
    assert ("dist/" in names) != ("dist" in names)
