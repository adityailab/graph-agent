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
