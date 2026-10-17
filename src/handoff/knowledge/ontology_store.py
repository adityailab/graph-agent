"""Entity types the knowledge graph has learned, kept in handoff's home between runs."""

from __future__ import annotations

import json
import os
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


def _write_atomically(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, path)  # readers see the old file or the new one, never half of one


def save_learned(home: Path, graph_name: str, types: list[tuple[str, str]]) -> None:
    """Replace the saved learned types."""
    _write_atomically(_path(home, graph_name), types)


def _pending_path(home: Path, graph_name: str) -> Path:
    return _path(home, graph_name).with_name(
        _path(home, graph_name).name.replace("ontology-", "pending-")
    )


def load_pending(home: Path, graph_name: str) -> list[str]:
    """Ingested texts still waiting for the next round of learning (none if unreadable)."""
    try:
        return [str(t) for t in json.loads(_pending_path(home, graph_name).read_text())]
    except (OSError, ValueError, TypeError):
        return []


def save_pending(home: Path, graph_name: str, texts: list[str]) -> None:
    """Keep the waiting texts, so a restart does not lose them."""
    _write_atomically(_pending_path(home, graph_name), texts)
