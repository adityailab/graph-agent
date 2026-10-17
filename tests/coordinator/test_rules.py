from __future__ import annotations

from falkordb import Graph

from handoff.coordinator.rules import Thresholds, run_rules
from handoff.graph.edits import add_edit
from handoff.graph.messages import claim_pending_messages
from handoff.graph.needs import resolve_need
from handoff.graph.requests import add_request

MIN = 60_000


def _inbox(graph: Graph, session: str, role: str) -> list[str]:
    msgs = claim_pending_messages(graph, session_id=session, role=role, since=0, at=10**15)
    return [m.text for m in msgs]


def test_a_need_open_too_long_reminds_the_role_that_owes_it(two_sessions: Graph) -> None:
    # two_sessions: frontend raised need n1 for backend at t=113
    acted = run_rules(two_sessions, now=113 + 31 * MIN, thresholds=Thresholds())
    assert [a.rule for a in acted] == ["stale_need"]
    text = _inbox(two_sessions, "be", "backend")[0]
    assert "n1" in text
    assert "return avatarUrl" in text
    assert "coordinator" in text


def test_a_young_or_resolved_need_is_left_alone(two_sessions: Graph) -> None:
    assert run_rules(two_sessions, now=113 + 5 * MIN, thresholds=Thresholds()) == []
    resolve_need(two_sessions, need_id="n1", request_id="p3")
    assert run_rules(two_sessions, now=113 + 90 * MIN, thresholds=Thresholds()) == []


def test_each_subject_is_acted_on_once(two_sessions: Graph) -> None:
    late = 113 + 31 * MIN
    assert len(run_rules(two_sessions, now=late, thresholds=Thresholds())) == 1
    assert run_rules(two_sessions, now=late + MIN, thresholds=Thresholds()) == []
    assert len(_inbox(two_sessions, "be", "backend")) == 1


def test_two_roles_changing_one_file_are_told_about_each_other(two_sessions: Graph) -> None:
    add_edit(
        two_sessions,
        request_id="p3",
        edit_id="e9",
        tool="Edit",
        path="Card.tsx",
        summary="x",
        at=215,
    )
    acted = run_rules(two_sessions, now=220, thresholds=Thresholds())
    assert [a.rule for a in acted] == ["collision"]
    assert "backend" in _inbox(two_sessions, "fe", "frontend")[0]
    assert "frontend" in _inbox(two_sessions, "be", "backend")[0]


def test_old_collisions_are_ignored(two_sessions: Graph) -> None:
    add_edit(
        two_sessions,
        request_id="p3",
        edit_id="e9",
        tool="Edit",
        path="Card.tsx",
        summary="x",
        at=215,
    )
    assert (
        run_rules(two_sessions, now=215 + 90 * MIN, thresholds=Thresholds(stale_minutes=10**6))
        == []
    )


def test_a_dry_run_changes_nothing(two_sessions: Graph) -> None:
    acted = run_rules(two_sessions, now=113 + 31 * MIN, thresholds=Thresholds(), dry_run=True)
    assert len(acted) == 1
    assert _inbox(two_sessions, "be", "backend") == []
    assert two_sessions.query("MATCH (a:Action) RETURN count(a)").result_set == [[0]]
    assert len(run_rules(two_sessions, now=113 + 31 * MIN, thresholds=Thresholds())) == 1


def test_the_digest_goes_to_the_person_once_an_hour(two_sessions: Graph) -> None:
    add_request(two_sessions, session_id="be", request_id="p4", text="more api", at=300)
    t = Thresholds(digest_minutes=60, stale_minutes=10**6)
    first = run_rules(two_sessions, now=400, thresholds=t)
    assert [a.rule for a in first] == ["digest"]
    assert run_rules(two_sessions, now=400 + 10 * MIN, thresholds=t) == []
    assert (
        run_rules(two_sessions, now=400 + 61 * MIN, thresholds=t) == []
    )  # a quiet hour: no digest
    add_request(two_sessions, session_id="fe", request_id="p5", text="polish", at=400 + 62 * MIN)
    again = run_rules(two_sessions, now=400 + 63 * MIN, thresholds=t)
    assert [a.rule for a in again] == ["digest"]
    text = two_sessions.query(
        "MATCH (m:Message {to_role: 'person'}) RETURN m.text ORDER BY m.at"
    ).result_set[0][0]
    assert "frontend" in text
    assert "open need" in text


def test_a_dry_run_skips_what_was_already_sent(two_sessions: Graph) -> None:
    late = 113 + 31 * MIN
    assert len(run_rules(two_sessions, now=late, thresholds=Thresholds())) == 1
    assert run_rules(two_sessions, now=late, thresholds=Thresholds(), dry_run=True) == []


def test_collision_text_states_facts_not_commands(two_sessions: Graph) -> None:
    add_edit(
        two_sessions,
        request_id="p3",
        edit_id="e9",
        tool="Edit",
        path="Card.tsx",
        summary="x",
        at=215,
    )
    (action,) = run_rules(two_sessions, now=220, thresholds=Thresholds())
    assert "Check the handoff" not in action.text
    assert "handoff shows" in action.text


def test_nudges_and_digests_are_not_facts_about_a_role(two_sessions: Graph) -> None:
    from handoff.graph.messages import role_messages

    add_request(two_sessions, session_id="be", request_id="p4", text="more api", at=300)
    t = Thresholds(digest_minutes=60)
    run_rules(two_sessions, now=113 + 31 * MIN, thresholds=t)
    kinds = two_sessions.query(
        "MATCH (:Session {role: 'coordinator'})-[:SENT]->(m:Message) RETURN DISTINCT m.kind"
    ).result_set
    assert sorted(k for (k,) in kinds) == ["digest", "nudge"]
    assert role_messages(two_sessions, role="backend", since=0, limit=10) == []


def test_a_claimed_action_always_comes_with_its_messages(two_sessions: Graph) -> None:
    add_edit(
        two_sessions,
        request_id="p3",
        edit_id="e9",
        tool="Edit",
        path="Card.tsx",
        summary="x",
        at=215,
    )
    run_rules(two_sessions, now=220, thresholds=Thresholds())
    run_rules(two_sessions, now=221, thresholds=Thresholds())
    rows = two_sessions.query(
        "MATCH (:Action {rule: 'collision'}) WITH count(*) AS actions "
        "MATCH (:Session {role: 'coordinator'})-[:SENT]->(m:Message) "
        "RETURN actions, count(m)"
    ).result_set
    assert rows == [[1, 2]]  # one collision, one message for each of the two roles


def test_a_need_still_open_much_later_is_reminded_again(two_sessions: Graph) -> None:
    t = Thresholds(stale_minutes=30, repeat_minutes=240)
    assert len(run_rules(two_sessions, now=113 + 31 * MIN, thresholds=t)) == 1
    assert run_rules(two_sessions, now=113 + 100 * MIN, thresholds=t) == []
    assert len(run_rules(two_sessions, now=113 + 241 * MIN, thresholds=t)) == 1
    assert len(_inbox(two_sessions, "be", "backend")) == 2


def test_a_collision_that_recurs_on_another_day_is_announced_again(two_sessions: Graph) -> None:
    day = 24 * 60 * MIN
    add_edit(
        two_sessions,
        request_id="p3",
        edit_id="e9",
        tool="Edit",
        path="Card.tsx",
        summary="x",
        at=215,
    )
    first = run_rules(two_sessions, now=220, thresholds=Thresholds(stale_minutes=10**9))
    assert [a.rule for a in first] == ["collision"]
    add_edit(
        two_sessions,
        request_id="p1",
        edit_id="e20",
        tool="Edit",
        path="Card.tsx",
        summary="y",
        at=day + 1000,
    )
    add_edit(
        two_sessions,
        request_id="p3",
        edit_id="e21",
        tool="Edit",
        path="Card.tsx",
        summary="z",
        at=day + 2000,
    )
    later = run_rules(two_sessions, now=day + 3000, thresholds=Thresholds(stale_minutes=10**9))
    assert [a.rule for a in later] == ["collision"]


def _backend_decides_on_profile(graph: Graph) -> None:
    from handoff.graph.decisions import add_decision

    add_decision(
        graph, request_id="p3", decision_id="d2", text="urls come from the CDN",
        reason="cheaper", topic="profile", at=300,
    )  # fmt: skip


def test_two_roles_with_decisions_on_one_topic_are_told_about_each_other(
    two_sessions: Graph,
) -> None:
    _backend_decides_on_profile(two_sessions)
    acted = run_rules(two_sessions, now=300 + MIN, thresholds=Thresholds())
    assert [a.rule for a in acted] == ["shared_topic"]
    for session, role in (("fe", "frontend"), ("be", "backend")):
        (text,) = _inbox(two_sessions, session, role)
        assert "profile" in text
        assert "supersede_decision" in text


def test_a_replaced_decision_ends_the_shared_topic(two_sessions: Graph) -> None:
    from handoff.graph.timeline import supersede_decision

    _backend_decides_on_profile(two_sessions)
    supersede_decision(two_sessions, new_id="d2", old_id="d1", at=301)
    assert run_rules(two_sessions, now=300 + MIN, thresholds=Thresholds()) == []


def test_a_shared_topic_is_announced_once(two_sessions: Graph) -> None:
    _backend_decides_on_profile(two_sessions)
    assert len(run_rules(two_sessions, now=300 + MIN, thresholds=Thresholds())) == 1
    assert run_rules(two_sessions, now=300 + 2 * MIN, thresholds=Thresholds()) == []
