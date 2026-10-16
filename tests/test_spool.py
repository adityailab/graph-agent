from __future__ import annotations

import fcntl
import json
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from handoff.spool import MAX_REPLAY, append, replay


def test_replay_applies_events_in_order_and_empties_the_file(tmp_path: Path) -> None:
    for i in range(3):
        append(tmp_path, {"n": i})
    seen: list[Any] = []
    assert replay(tmp_path, lambda e: seen.append(e["n"]), is_outage=_outage).applied == 3
    assert seen == [0, 1, 2]
    assert replay(tmp_path, lambda e: seen.append(e["n"]), is_outage=_outage).applied == 0


class OutageError(Exception):
    pass


def _outage(exc: Exception) -> bool:
    return isinstance(exc, OutageError)


def test_replay_stops_at_the_first_outage_and_keeps_the_rest_in_order(tmp_path: Path) -> None:
    for i in range(4):
        append(tmp_path, {"n": i})

    def apply(event: dict[str, Any]) -> None:
        if event["n"] == 1:
            raise OutageError

    result = replay(tmp_path, apply, is_outage=_outage)
    assert (result.applied, result.pending) == (1, True)
    left: list[Any] = []
    replay(tmp_path, lambda e: left.append(e["n"]), is_outage=_outage)
    assert left == [1, 2, 3]


def test_event_failing_for_another_reason_moves_to_the_dead_letter_file(tmp_path: Path) -> None:
    for i in range(3):
        append(tmp_path, {"n": i})

    def apply(event: dict[str, Any]) -> None:
        if event["n"] == 1:
            raise ValueError("bad event")

    result = replay(tmp_path, apply, is_outage=_outage)
    assert (result.applied, result.pending) == (2, False)
    assert '"n": 1' in (tmp_path / "spool.dead.jsonl").read_text()


def test_replay_is_capped_per_call(tmp_path: Path) -> None:
    for i in range(MAX_REPLAY + 5):
        append(tmp_path, {"n": i})
    result = replay(tmp_path, lambda e: None, is_outage=_outage)
    assert (result.applied, result.pending) == (MAX_REPLAY, True)


def test_busy_replay_file_reports_pending(tmp_path: Path) -> None:
    append(tmp_path, {"n": 0})
    with (tmp_path / "spool.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = replay(tmp_path, lambda e: None, is_outage=_outage)
    assert (result.applied, result.pending) == (0, True)


def test_spool_files_are_private(tmp_path: Path) -> None:
    append(tmp_path, {"n": 0})
    assert stat.S_IMODE((tmp_path / "spool.jsonl").stat().st_mode) == 0o600


def test_undecodable_line_is_moved_aside_and_replay_continues(tmp_path: Path) -> None:
    append(tmp_path, {"n": 1})
    with (tmp_path / "spool.jsonl").open("ab") as f:
        f.write(b"\xff\xfe broken\n")
    append(tmp_path, {"n": 2})
    seen: list[Any] = []
    assert replay(tmp_path, lambda e: seen.append(e["n"]), is_outage=_outage).applied == 2
    assert seen == [1, 2]


def test_replay_without_a_file_does_nothing(tmp_path: Path) -> None:
    assert replay(tmp_path / "missing", lambda e: None, is_outage=_outage).applied == 0


def test_unreadable_line_is_dropped(tmp_path: Path) -> None:
    append(tmp_path, {"n": 1})
    with (tmp_path / "spool.jsonl").open("a") as f:
        f.write("{not json\n")
    seen: list[Any] = []
    assert replay(tmp_path, lambda e: seen.append(e["n"]), is_outage=_outage).applied == 1
    assert seen == [1]


def test_two_processes_appending_at_once_write_whole_lines(tmp_path: Path) -> None:
    script = (
        "import sys; from pathlib import Path; from handoff.spool import append\n"
        "for i in range(200):\n"
        "    append(Path(sys.argv[1]), {'w': sys.argv[2], 'i': i, 'pad': 'x' * 500})"
    )
    procs = [subprocess.Popen([sys.executable, "-c", script, str(tmp_path), name]) for name in "ab"]
    for p in procs:
        assert p.wait(timeout=60) == 0
    lines = (tmp_path / "spool.jsonl").read_text().splitlines()
    assert len(lines) == 400
    assert all(json.loads(line)["w"] in "ab" for line in lines)
