from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.consultations import add_consultations
from handoff.graph.conventions import add_convention
from handoff.graph.decisions import add_decision
from handoff.graph.memory_items import memory_items, relevant_memories
from handoff.graph.messages import add_message
from handoff.graph.timeline import supersede_decision


def _texts(graph: Graph, kind: str) -> list[str]:
    return [i.text for i in memory_items(graph, kind, since=0, limit=50)]


def test_working_items_are_what_each_live_session_is_on(two_sessions: Graph) -> None:
    items = memory_items(two_sessions, "working", since=0, limit=50)
    assert {(i.title, i.text) for i in items} == {
        ("frontend", "tidy styles"),
        ("backend", "pick up frontend"),
    }


def test_episodic_items_list_requests_and_edits_newest_first(two_sessions: Graph) -> None:
    items = memory_items(two_sessions, "episodic", since=0, limit=50)
    assert [i.at for i in items] == sorted((i.at for i in items), reverse=True)
    assert {"show avatar", "Card.tsx"} <= {i.text for i in items} | {
        i.text.split(" ")[0] for i in items
    }
    assert {i.title for i in items} >= {"request", "edit"}


def test_semantic_items_are_decisions_with_their_topic_and_reason(two_sessions: Graph) -> None:
    [item] = memory_items(two_sessions, "semantic", since=0, limit=50)
    assert item.title == "decision · profile"
    assert "read avatarUrl" in item.text
    assert "server owns urls" in item.text
    assert item.role == "frontend"


def test_procedural_items_are_the_rules_in_force(two_sessions: Graph) -> None:
    add_convention(
        two_sessions,
        convention_id="c1",
        text="amounts in paise",
        reason="no floats",
        scope="all",
        author="person",
        at=300,
    )
    [item] = memory_items(two_sessions, "procedural", since=0, limit=50)
    assert item.title == "rule · all"
    assert "amounts in paise" in item.text
    assert "no floats" in item.text


def test_temporal_items_are_the_whole_timeline_oldest_first_with_times(two_sessions: Graph) -> None:
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
    items = memory_items(two_sessions, "temporal", since=0, limit=50, oldest_first=True)
    assert [i.at for i in items] == sorted(i.at for i in items)
    assert {"request", "decision", "edit", "replaced"} <= {i.title for i in items}
    replaced = next(i for i in items if i.title == "replaced")
    assert "read avatarUrl" in replaced.text
    assert "read avatar_url" in replaced.text
    assert all(i.at > 0 for i in items)
    assert replaced.at == 300  # when the replacing decision was made, not an unset link time


def test_social_items_are_messages_and_reads(two_sessions: Graph) -> None:
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p1"], at=230)
    add_message(
        two_sessions,
        message_id="m1",
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text="hi there",
        reply_to=None,
        at=240,
    )
    items = memory_items(two_sessions, "social", since=0, limit=50)
    assert {i.title for i in items} == {"backend → frontend", "backend read frontend"}
    assert any(i.text == "hi there" for i in items)


def test_the_limit_caps_how_many_items_come_back(two_sessions: Graph) -> None:
    assert len(memory_items(two_sessions, "episodic", since=0, limit=2)) == 2


def test_an_unknown_kind_is_refused(two_sessions: Graph) -> None:
    with pytest.raises(ValueError, match="unknown kind"):
        memory_items(two_sessions, "dreams", since=0, limit=5)


def test_relevant_memories_are_decisions_matching_the_words_of_a_task(two_sessions: Graph) -> None:
    [item] = relevant_memories(two_sessions, "show the avatarUrl on the card", k=5)
    assert item.title == "decision · frontend"
    assert "read avatarUrl" in item.text


def test_nothing_is_relevant_to_an_unrelated_task(two_sessions: Graph) -> None:
    assert relevant_memories(two_sessions, "paint the garage", k=5) == []


def test_a_replaced_decision_is_not_offered_as_relevant(two_sessions: Graph) -> None:
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
    texts = [i.text for i in relevant_memories(two_sessions, "avatar read the url", k=5)]
    assert any("avatar_url" in t for t in texts)
    assert not any("avatarUrl" in t for t in texts)


def test_relevant_memories_carry_their_time(two_sessions: Graph) -> None:
    [item] = relevant_memories(two_sessions, "show the avatarUrl", k=5)
    assert item.at == 112


def test_an_agreement_between_roles_is_on_the_timeline(two_sessions: Graph) -> None:
    from handoff.graph.agreements import link_agreements
    from handoff.graph.decisions import set_decision_embedding
    from handoff.graph.schema import EMBED_DIM

    vec = [1.0] + [0.0] * (EMBED_DIM - 1)
    set_decision_embedding(two_sessions, "d1", vec)
    add_decision(
        two_sessions,
        request_id="p3",
        decision_id="d2",
        text="avatar url from server",
        reason="r",
        topic="profile",
        at=300,
    )
    set_decision_embedding(two_sessions, "d2", vec)
    link_agreements(two_sessions, "d2", vec, role="backend", at=310)
    items = memory_items(two_sessions, "temporal", since=0, limit=50, oldest_first=True)
    agreed = next(i for i in items if i.title == "agrees")
    assert agreed.role == "backend"
    assert "frontend" in agreed.text
    assert "read avatarUrl" in agreed.text
    assert agreed.at == 310
