from __future__ import annotations

import time
from pathlib import Path

import pytest
from falkordb import Graph
from redis.exceptions import ResponseError

from handoff.coordinator.rules import Thresholds
from handoff.coordinator.runner import Coordinator


def test_a_pass_acts_and_the_loop_keeps_going_after_a_failure(
    two_sessions: Graph, tmp_path: Path
) -> None:
    calls = {"n": 0}

    def flaky(
        graph: Graph, *, now: int, thresholds: Thresholds, dry_run: bool = False
    ) -> list[object]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ResponseError("database blip")
        return []

    coordinator = Coordinator(
        graph=two_sessions,
        home=tmp_path,
        lock_name="t",
        thresholds=Thresholds(),
        interval=0.01,
        rules=flaky,
    )
    thread = coordinator.start()
    deadline = time.monotonic() + 5
    while calls["n"] < 3 and time.monotonic() < deadline:
        time.sleep(0.02)
    coordinator.stop()
    thread.join(timeout=5)
    assert calls["n"] >= 3  # it survived the first pass failing
    assert Coordinator(
        graph=two_sessions, home=tmp_path, lock_name="t", thresholds=Thresholds()
    ).try_lead()  # lock released on stop


def test_a_second_coordinator_for_the_same_graph_stands_by(
    two_sessions: Graph, tmp_path: Path
) -> None:
    one = Coordinator(graph=two_sessions, home=tmp_path, lock_name="g", thresholds=Thresholds())
    two = Coordinator(graph=two_sessions, home=tmp_path, lock_name="g", thresholds=Thresholds())
    assert one.try_lead() is True
    assert two.try_lead() is False
    one.stand_down()


def test_the_loop_reports_what_it_does(
    two_sessions: Graph, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from handoff.coordinator.rules import Action

    def acts(
        graph: Graph, *, now: int, thresholds: Thresholds, dry_run: bool = False
    ) -> list[Action]:
        return [Action("stale_need", ("backend",), "Reminder: need n1")]

    caplog.set_level("INFO")
    coordinator = Coordinator(
        graph=two_sessions,
        home=tmp_path,
        lock_name="r",
        thresholds=Thresholds(),
        interval=0.01,
        rules=acts,
    )
    thread = coordinator.start()
    deadline = time.monotonic() + 5
    while "stale_need" not in caplog.text and time.monotonic() < deadline:
        time.sleep(0.02)
    coordinator.stop()
    thread.join(timeout=5)
    assert "stale_need" in caplog.text
    assert "backend" in caplog.text


def test_a_dry_run_loop_names_each_action_once(
    two_sessions: Graph, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from handoff.coordinator.rules import Action

    def acts(
        graph: Graph, *, now: int, thresholds: Thresholds, dry_run: bool = False
    ) -> list[Action]:
        return [Action("stale_need", ("backend",), "Reminder: need n1")]

    caplog.set_level("INFO")
    coordinator = Coordinator(
        graph=two_sessions,
        home=tmp_path,
        lock_name="d",
        thresholds=Thresholds(),
        interval=0.01,
        rules=acts,
        dry_run=True,
    )
    thread = coordinator.start()
    time.sleep(0.3)
    coordinator.stop()
    thread.join(timeout=5)
    assert caplog.text.count("would send") == 1
