"""Settings read from the environment."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Where the graph lives and where local files (replay file, locks, logs) go."""

    host: str
    port: int
    graph_name: str
    home: Path

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        """Build a config from environment variables, with local defaults."""
        source = os.environ if env is None else env
        return cls(
            host=source.get("HANDOFF_DB_HOST", "localhost"),
            port=int(source.get("HANDOFF_DB_PORT", "6379")),
            graph_name=source.get("HANDOFF_GRAPH", "handoff"),
            home=Path(source.get("HANDOFF_HOME", str(Path.home() / ".handoff"))),
        )


def normalise_role(role: str) -> str:
    """Roles match without regard to case or surrounding spaces."""
    return role.strip().lower()


def resolve_role(cwd: str, env: Mapping[str, str]) -> str:
    """Return the session's role: HANDOFF_ROLE, else the folder name, else 'unknown'."""
    return normalise_role(env.get("HANDOFF_ROLE", "") or Path(cwd).name) or "unknown"


def graph_for_workspace(workspace: Path) -> str:
    """A graph name of this workspace's own, so separate projects never see each other's
    work: the folder name made safe, plus a short hash of its full path."""
    slug = re.sub(r"[^a-z0-9]+", "_", workspace.name.lower()).strip("_") or "workspace"
    digest = hashlib.sha256(str(workspace.resolve()).encode()).hexdigest()[:6]
    return f"handoff_{slug}_{digest}"
