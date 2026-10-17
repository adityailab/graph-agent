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
