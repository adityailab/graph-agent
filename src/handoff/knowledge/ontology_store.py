"""Entity types the knowledge graph has learned, kept in handoff's home between runs."""

from __future__ import annotations

import json
import re
from pathlib import Path


def _path(home: Path, graph_name: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", graph_name) or "_"
    return home / f"ontology-{safe}.json"


def load_learned(home: Path, graph_name: str) -> list[tuple[str, str]]:
    """The learned (label, description) pairs for a graph; none if the file is missing or
    unreadable (learning then simply starts over)."""
    try:
        data = json.loads(_path(home, graph_name).read_text())
        return [(str(item[0]), str(item[1])) for item in data]
    except (OSError, ValueError, IndexError, TypeError):
        return []


def save_learned(home: Path, graph_name: str, types: list[tuple[str, str]]) -> None:
    """Replace the saved learned types."""
    home.mkdir(parents=True, exist_ok=True)
    _path(home, graph_name).write_text(json.dumps(types))
