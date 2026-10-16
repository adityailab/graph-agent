from __future__ import annotations

from falkordb import Graph

from handoff.graph.knowledge import describe_items, entity_documents, find_entities


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
