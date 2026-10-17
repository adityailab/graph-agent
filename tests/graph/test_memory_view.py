from __future__ import annotations

from falkordb import Graph

from handoff.graph.consultations import add_consultations
from handoff.graph.conventions import add_convention
from handoff.graph.decisions import add_decision
from handoff.graph.memory_view import memory_types, role_contexts
from handoff.graph.messages import add_message, claim_pending_messages
from handoff.graph.timeline import supersede_decision


def _by_key(graph: Graph) -> dict[str, int]:
    return {t.key: t.count for t in memory_types(graph, concepts=0, since=0)}


def test_every_kind_of_memory_is_reported_in_a_fixed_order(two_sessions: Graph) -> None:
    keys = [t.key for t in memory_types(two_sessions, concepts=0, since=0)]
    assert keys == ["working", "episodic", "semantic", "procedural", "temporal", "social"]


def test_working_memory_counts_live_sessions(two_sessions: Graph) -> None:
    assert _by_key(two_sessions)["working"] == 2


def test_episodic_memory_counts_what_happened(two_sessions: Graph) -> None:
    counts = {t.key: t for t in memory_types(two_sessions, concepts=0, since=0)}
    assert counts["episodic"].count == 3 + 2 + 0  # requests + edits + messages
    assert "3 requests" in counts["episodic"].detail


def test_semantic_memory_counts_topics_decisions_and_concepts(two_sessions: Graph) -> None:
    kinds = {t.key: t for t in memory_types(two_sessions, concepts=5, since=0)}
    assert kinds["semantic"].count == 1 + 1 + 5
    assert "5 concepts" in kinds["semantic"].detail


def test_procedural_memory_counts_rules_in_force(two_sessions: Graph) -> None:
    add_convention(
        two_sessions,
        convention_id="c1",
        text="paise",
        reason="r",
        scope="all",
        author="person",
        at=1,
    )
    assert _by_key(two_sessions)["procedural"] == 1


def test_temporal_memory_counts_the_timeline_and_names_what_was_replaced(
    two_sessions: Graph,
) -> None:
    add_decision(
        two_sessions,
        request_id="p3",
        decision_id="d2",
        text="CDN",
        reason="r",
        topic="profile",
        at=300,
    )
    supersede_decision(two_sessions, new_id="d2", old_id="d1", at=301)
    temporal = {t.key: t for t in memory_types(two_sessions, concepts=0, since=0)}["temporal"]
    # everything on the timeline: 3 requests, 2 edits, 2 decisions, 0 messages, 1 replacement
    assert temporal.count == 3 + 2 + 2 + 0 + 1
    assert "1 decision replaced" in temporal.detail
    assert "spanning" in temporal.detail


def test_social_memory_counts_reads_and_messages(two_sessions: Graph) -> None:
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p1"], at=230)
    add_message(
        two_sessions,
        message_id="m1",
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text="hi",
        reply_to=None,
        at=240,
    )
    assert _by_key(two_sessions)["social"] == 2


def test_a_role_context_shows_what_it_is_on_what_it_learned_and_what_reached_it(
    two_sessions: Graph,
) -> None:
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p1"], at=230)
    add_message(
        two_sessions,
        message_id="m1",
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text="hi",
        reply_to=None,
        at=240,
    )
    claim_pending_messages(two_sessions, session_id="fe", role="frontend", since=0, at=250)
    add_convention(
        two_sessions,
        convention_id="c1",
        text="paise",
        reason="r",
        scope="backend",
        author="person",
        at=1,
    )
    contexts = {c.role: c for c in role_contexts(two_sessions, since=0)}
    backend, frontend = contexts["backend"], contexts["frontend"]
    assert backend.working_on == "pick up frontend"
    assert [(who, text) for who, text in backend.learned] == [("frontend", "read avatarUrl")]
    assert frontend.inbox == 1
    assert (backend.rules, frontend.rules) == (1, 0)
    assert backend.open_needs == 1
