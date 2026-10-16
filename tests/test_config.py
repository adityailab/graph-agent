from __future__ import annotations

from pathlib import Path

from handoff.config import Config, resolve_role


def test_config_reads_environment(tmp_path: Path) -> None:
    env = {
        "HANDOFF_DB_HOST": "db",
        "HANDOFF_DB_PORT": "6390",
        "HANDOFF_GRAPH": "g1",
        "HANDOFF_HOME": str(tmp_path),
    }
    assert Config.from_env(env) == Config(host="db", port=6390, graph_name="g1", home=tmp_path)


def test_config_defaults() -> None:
    config = Config.from_env({})
    assert (config.host, config.port, config.graph_name) == ("localhost", 6379, "handoff")
    assert config.home == Path.home() / ".handoff"


def test_role_prefers_environment() -> None:
    assert resolve_role("/work/frontend", {"HANDOFF_ROLE": "web"}) == "web"


def test_role_falls_back_to_folder_name() -> None:
    assert resolve_role("/work/backend", {}) == "backend"


def test_role_for_filesystem_root_is_unknown() -> None:
    assert resolve_role("/", {}) == "unknown"
