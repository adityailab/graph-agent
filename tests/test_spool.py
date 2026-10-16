from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from handoff.spool import append, replay


def test_replay_applies_events_in_order_and_empties_the_file(tmp_path: Path) -> None:
    for i in range(3):
        append(tmp_path, {"n": i})
    seen: list[Any] = []
    assert replay(tmp_path, lambda e: seen.append(e["n"])) == 3
    assert seen == [0, 1, 2]
    assert replay(tmp_path, lambda e: seen.append(e["n"])) == 0


def test_failing_event_is_kept_and_later_ones_still_apply(tmp_path: Path) -> None:
    for i in range(3):
        append(tmp_path, {"n": i})

    def apply(event: dict[str, Any]) -> None:
        if event["n"] == 1:
            raise RuntimeError("database still down")

    assert replay(tmp_path, apply) == 2
    kept: list[Any] = []
    assert replay(tmp_path, lambda e: kept.append(e["n"])) == 1
    assert kept == [1]


def test_replay_without_a_file_does_nothing(tmp_path: Path) -> None:
    assert replay(tmp_path / "missing", lambda e: None) == 0


def test_unreadable_line_is_dropped(tmp_path: Path) -> None:
    append(tmp_path, {"n": 1})
    with (tmp_path / "spool.jsonl").open("a") as f:
        f.write("{not json\n")
    seen: list[Any] = []
    assert replay(tmp_path, lambda e: seen.append(e["n"])) == 1
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
    seen: list[Any] = []
    assert replay(tmp_path, seen.append) == 400
