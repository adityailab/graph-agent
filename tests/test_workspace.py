from __future__ import annotations

from pathlib import Path

from handoff.config import graph_for_workspace
from handoff.workspace import workspace_config, workspace_graph


def _settings(folder: Path, text: str) -> None:
    (folder / ".claude").mkdir(exist_ok=True)
    (folder / ".claude" / "settings.local.json").write_text(text)


def test_an_installed_folder_uses_the_graph_in_its_settings(tmp_path: Path) -> None:
    _settings(tmp_path, '{"env": {"HANDOFF_GRAPH": "shop"}}')
    assert workspace_graph(tmp_path, {"HANDOFF_GRAPH": "other"}) == "shop"


def test_otherwise_the_environment_then_the_folder_default(tmp_path: Path) -> None:
    assert workspace_graph(tmp_path, {"HANDOFF_GRAPH": "g"}) == "g"
    assert workspace_graph(tmp_path, {}) == graph_for_workspace(tmp_path)


def test_broken_or_odd_settings_fall_back(tmp_path: Path) -> None:
    for text in ("{not json", '{"env": null}', '["a list"]', '{"env": {"HANDOFF_GRAPH": 5}}'):
        _settings(tmp_path, text)
        assert workspace_graph(tmp_path, {}) == graph_for_workspace(tmp_path)


def test_the_config_carries_the_workspace_graph(tmp_path: Path) -> None:
    _settings(tmp_path, '{"env": {"HANDOFF_GRAPH": "shop"}}')
    config = workspace_config(tmp_path, {"HANDOFF_DB_PORT": "6390"})
    assert (config.graph_name, config.port) == ("shop", 6390)
