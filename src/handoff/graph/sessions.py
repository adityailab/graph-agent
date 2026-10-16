"""Queries about sessions: one per running Claude Code terminal."""

from __future__ import annotations

from falkordb import Graph


def upsert_session(graph: Graph, *, session_id: str, role: str, cwd: str, at: int) -> None:
    """Create the session on first sight; refresh its role, folder and last-seen time."""
    graph.query(
        "MERGE (s:Session {id: $id}) "
        "ON CREATE SET s.started_at = $at "
        "SET s.role = $role, s.cwd = $cwd, s.last_seen_at = $at",
        {"id": session_id, "role": role, "cwd": cwd, "at": at},
    )
