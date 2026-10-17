from __future__ import annotations

from pathlib import Path

import pytest

from handoff.config import Config
from handoff.database import CONTAINER, DATA_DIR, IMAGE, DatabaseUnavailable, ensure_database
from tests.cli.fakes import fake_runner


def test_a_reachable_database_is_used_as_is(config: Config) -> None:
    calls: list[list[str]] = []
    assert ensure_database(config, fake_runner(calls)) == "running"
    assert calls == []  # never touches docker, so this repo's own container is left alone


def test_a_stopped_container_is_started(tmp_path: Path) -> None:
    down = Config("localhost", 1, "g", tmp_path)
    calls: list[list[str]] = []
    runner = fake_runner(calls, {("docker", "ps", "-a"): f"{CONTAINER}\n"})
    with pytest.raises(DatabaseUnavailable):  # nothing really starts on port 1
        ensure_database(down, runner, wait_seconds=0.2)
    assert ["docker", "start", CONTAINER] in calls
    assert not any(c[:2] == ["docker", "run"] for c in calls)


def test_without_a_container_the_pinned_image_runs_on_localhost(tmp_path: Path) -> None:
    down = Config("localhost", 1, "g", tmp_path)
    calls: list[list[str]] = []
    with pytest.raises(DatabaseUnavailable):
        ensure_database(down, fake_runner(calls, {("docker", "ps", "-a"): ""}), wait_seconds=0.2)
    run = next(c for c in calls if c[:2] == ["docker", "run"])
    assert run[2:] == [
        "-d",
        "--name",
        CONTAINER,
        "-p",
        "127.0.0.1:1:6379",
        "-p",
        "127.0.0.1:3000:3000",
        "-v",
        f"handoff-data:{DATA_DIR}",
        IMAGE,
    ]


def test_a_remote_database_is_never_started_here(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    with pytest.raises(DatabaseUnavailable, match=r"db\.example\.com"):
        ensure_database(Config("db.example.com", 1, "g", tmp_path), fake_runner(calls))
    assert calls == []


def test_a_failing_docker_command_is_reported(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    with pytest.raises(DatabaseUnavailable, match="docker"):
        ensure_database(Config("localhost", 1, "g", tmp_path), fake_runner(calls, code=1))
