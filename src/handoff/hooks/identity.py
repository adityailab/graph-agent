"""Which session a hook belongs to: its project folder and role."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from handoff.config import resolve_role


def project_and_role(data: Mapping[str, Any], env: Mapping[str, str]) -> tuple[str, str]:
    """Return the resolved project folder and the session's role.

    The project folder, not the shell's current folder: the agent may `cd`, and the
    MCP server finds this session again by role and project folder.
    """
    project_dir = str(Path(env.get("CLAUDE_PROJECT_DIR") or str(data.get("cwd", ""))).resolve())
    return project_dir, resolve_role(project_dir, env)
