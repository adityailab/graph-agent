from __future__ import annotations

import fcntl

from handoff.config import Config
from handoff.knowledge.lead import is_leading, lock_name, lock_path


def test_no_lock_file_means_no_worker(config: Config) -> None:
    assert is_leading(config) is False


def test_a_held_lock_means_a_worker_is_running(config: Config) -> None:
    path = lock_path(config)
    path.parent.mkdir(parents=True)
    with path.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert is_leading(config) is True
    assert is_leading(config) is False


def test_the_lock_is_per_graph_and_server(config: Config) -> None:
    assert lock_name(config) == f"{config.host}-{config.port}-{config.graph_name}"
    assert lock_path(config).name == f"knowledge-{lock_name(config)}.lock"
