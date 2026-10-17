from __future__ import annotations

from falkordb import Graph

from handoff.dashboard.quick import quick_answer
from handoff.graph.consultations import add_consultations
from handoff.graph.conventions import add_convention
from handoff.graph.decisions import add_decision
from handoff.graph.timeline import supersede_decision


def _answer(graph: Graph, question: str) -> str | None:
    found = quick_answer(graph, question, since=0)
    return None if found is None else found.answer


def test_what_each_session_is_working_on_is_answered_from_the_graph(two_sessions: Graph) -> None:
    text = _answer(two_sessions, "What is each session working on right now?")
    assert text is not None
    assert "frontend" in text
    assert "tidy styles" in text
    assert "backend" in text
    assert "pick up frontend" in text


def test_standing_rules_are_listed_with_their_reasons(two_sessions: Graph) -> None:
    add_convention(
        two_sessions,
        convention_id="c1",
        text="amounts in paise",
        reason="no floats",
        scope="all",
        author="person",
        at=300,
    )
    text = _answer(two_sessions, "Which standing rules are in force?")
    assert text is not None
    assert "amounts in paise" in text
    assert "no floats" in text


def test_no_rules_says_so(two_sessions: Graph) -> None:
    assert "No standing rules" in (_answer(two_sessions, "which rules are in force?") or "")


def test_replaced_decisions_show_what_replaced_them(two_sessions: Graph) -> None:
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
    text = _answer(two_sessions, "Which decisions were replaced, and by what?")
    assert text is not None
    assert "read avatarUrl" in text
    assert "read avatar_url" in text


def test_nothing_replaced_says_so(two_sessions: Graph) -> None:
    assert "No decision has been replaced" in (_answer(two_sessions, "what was replaced?") or "")


def test_who_read_whose_work(two_sessions: Graph) -> None:
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p1"], at=230)
    text = _answer(two_sessions, "Who has read whose work?")
    assert text is not None
    assert "backend" in text
    assert "frontend" in text


def test_an_answer_says_where_it_came_from_and_that_no_model_was_used(
    two_sessions: Graph,
) -> None:
    found = quick_answer(two_sessions, "which rules are in force?", since=0)
    assert found is not None
    assert found.source


def test_a_question_it_does_not_know_goes_to_the_model(two_sessions: Graph) -> None:
    assert quick_answer(two_sessions, "why did frontend choose avatarUrl?", since=0) is None
    assert quick_answer(two_sessions, "how many edits touched Card.tsx last week", since=0) is None
