from __future__ import annotations

import time
from pathlib import Path

from falkordb import Graph

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
            raise RuntimeError("database blip")
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
