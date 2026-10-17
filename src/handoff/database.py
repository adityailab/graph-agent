"""Making sure a FalkorDB answers: use one that runs, else start ours in Docker."""

from __future__ import annotations

import time

from handoff.cli.runner import Runner
from handoff.config import Config
from handoff.graph.connection import server_reachable

IMAGE = "falkordb/falkordb:v4.22.1"
CONTAINER = "handoff-falkordb"
VOLUME = "handoff-data"
DATA_DIR = "/var/lib/falkordb/data"  # the image's FALKORDB_DATA_PATH
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


class DatabaseUnavailable(RuntimeError):  # noqa: N818 - reads as a state, like ModelUnavailable
    """FalkorDB could not be reached or started; the message says why."""


def _docker(runner: Runner, args: list[str]) -> str:
    try:
        done = runner(["docker", *args])
    except (FileNotFoundError, OSError) as exc:
        raise DatabaseUnavailable(f"docker could not run: {exc}") from exc
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip().splitlines()
        raise DatabaseUnavailable(
            f"docker {args[0]} failed: {detail[0] if detail else 'no output'}"
        )
    return done.stdout


def _start_container(config: Config, runner: Runner) -> str:
    existing = _docker(
        runner, ["ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Names}}"]
    )
    if CONTAINER in existing.split():
        _docker(runner, ["start", CONTAINER])
        return "started"
    _docker(
        runner,
        [
            "run",
            "-d",
            "--name",
            CONTAINER,
            "-p",
            f"127.0.0.1:{config.port}:6379",
            "-p",
            "127.0.0.1:3000:3000",
            "-v",
            f"{VOLUME}:{DATA_DIR}",
            IMAGE,
        ],
    )
    return "created"


def ensure_database(config: Config, runner: Runner, *, wait_seconds: float = 30) -> str:
    """'running' if FalkorDB already answers; otherwise start ours ('started' or
    'created') and wait for it. Never starts anything for a remote host, and never
    deletes a container or its data."""
    if server_reachable(config):
        return "running"
    if config.host not in _LOCAL_HOSTS:
        raise DatabaseUnavailable(f"FalkorDB at {config.host}:{config.port} does not answer.")
    status = _start_container(config, runner)
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if server_reachable(config):
            return status
        time.sleep(0.5)
    raise DatabaseUnavailable(f"FalkorDB did not answer on port {config.port} after starting.")
