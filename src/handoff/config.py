"""Settings read from the environment."""

from __future__ import annotations

import os
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
