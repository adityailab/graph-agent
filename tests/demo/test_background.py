from __future__ import annotations

import json
import socket
import time
import urllib.request
from pathlib import Path

from handoff.demo.background import stop_from_pid_file
from handoff.demo.mission import start_mission_control


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_mission_control_runs_in_the_background_and_stops(tmp_path: Path) -> None:
    folder, state, port = tmp_path / "shop", tmp_path / "state", _free_port()
    folder.mkdir()
    url = start_mission_control(folder, state, port=port)
    try:
        assert url == f"http://127.0.0.1:{port}/"
        for _ in range(100):  # the process needs a moment to import and bind
            try:
                with urllib.request.urlopen(url + "api/state", timeout=2) as response:
                    assert "graph" in json.loads(response.read())
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError((state / "dashboard.log").read_text())
    finally:
        stop_from_pid_file(state / "dashboard.pid")
    assert not (state / "dashboard.pid").exists()


def test_stopping_with_no_pid_file_is_harmless(tmp_path: Path) -> None:
    stop_from_pid_file(tmp_path / "missing.pid")
