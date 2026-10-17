"""Which graph a project folder uses, so every handoff command agrees with its sessions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from handoff.config import Config, graph_for_workspace


def _settings_graph(folder: Path) -> str | None:
    path = folder / ".claude" / "settings.local.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    env = data.get("env") if isinstance(data, dict) else None
    graph = env.get("HANDOFF_GRAPH") if isinstance(env, dict) else None
    return graph if isinstance(graph, str) and graph else None


def workspace_graph(folder: Path, env: Mapping[str, str]) -> str:
    """The folder's graph: as installed in its settings, else HANDOFF_GRAPH, else the
    folder's own default name."""
    return _settings_graph(folder) or env.get("HANDOFF_GRAPH") or graph_for_workspace(folder)


def workspace_config(folder: Path, env: Mapping[str, str]) -> Config:
    """Config.from_env, with the folder's graph."""
    return Config.from_env({**env, "HANDOFF_GRAPH": workspace_graph(folder, env)})
