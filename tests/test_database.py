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


def test_a_slow_docker_command_is_one_sentence(tmp_path: Path) -> None:
    import subprocess

    def slow(argv: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("docker", 120)

    with pytest.raises(DatabaseUnavailable, match="timed out"):
        ensure_database(Config("localhost", 1, "g", tmp_path), slow, wait_seconds=0.2)


def test_the_image_is_pulled_as_its_own_step_before_it_runs(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    with pytest.raises(DatabaseUnavailable):
        ensure_database(
            Config("localhost", 1, "g", tmp_path),
            fake_runner(calls, {("docker", "ps", "-a"): ""}),
            wait_seconds=0.2,
        )
    verbs = [c[1] for c in calls if c[0] == "docker"]
    assert verbs.index("pull") < verbs.index("run")


def test_the_browser_port_can_be_moved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HANDOFF_BROWSER_PORT", "3100")
    calls: list[list[str]] = []
    with pytest.raises(DatabaseUnavailable):
        ensure_database(
            Config("localhost", 1, "g", tmp_path),
            fake_runner(calls, {("docker", "ps", "-a"): ""}),
            wait_seconds=0.2,
        )
    run = next(c for c in calls if c[:2] == ["docker", "run"])
    assert "127.0.0.1:3100:3000" in run


def test_plain_redis_on_the_port_is_not_taken_for_falkordb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from redis.exceptions import ResponseError

    class PlainRedis:
        def __init__(self, **kwargs: object) -> None:
            self.connection = self

        def ping(self) -> bool:
            return True

        def list_graphs(self) -> list[str]:
            raise ResponseError("unknown command 'GRAPH.LIST'")

    monkeypatch.setattr("handoff.graph.connection.FalkorDB", PlainRedis)
    calls: list[list[str]] = []
    with pytest.raises(DatabaseUnavailable, match="not FalkorDB"):
        ensure_database(Config("localhost", 6390, "g", tmp_path), fake_runner(calls))
    assert calls == []
