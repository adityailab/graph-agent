"""Queries about sessions: one per running Claude Code terminal."""

from __future__ import annotations

from typing import Any

from falkordb import Graph

from handoff.graph.records import SessionInfo

_SESSION_FIELDS = "s.id, s.role, s.cwd, s.started_at, s.last_seen_at"


def upsert_session(
    graph: Graph, *, session_id: str, role: str, cwd: str, at: int, pid: int | None = None
) -> None:
    """Create the session on first sight; refresh its role, folder, process and last-seen time.

    `pid` is the Claude Code process: it survives /clear, which starts a new session id.
    """
    graph.query(
        "MERGE (s:Session {id: $id}) "
        "ON CREATE SET s.started_at = $at "
        "SET s.role = $role, s.name = $role, "
        "s.cwd = $cwd, s.last_seen_at = $at, s.pid = coalesce($pid, s.pid)",
        {"id": session_id, "role": role, "cwd": cwd, "at": at, "pid": pid},
    )


def _session(row: list[Any]) -> SessionInfo:
    return SessionInfo(
        id=str(row[0]),
        role=str(row[1]),
        cwd=str(row[2]),
        started_at=int(row[3]),
        last_seen_at=int(row[4]),
    )


def active_session(graph: Graph, *, role: str, cwd: str) -> SessionInfo | None:
    """Return the most recently seen session with this role in this folder."""
    rows = graph.ro_query(
        f"MATCH (s:Session {{role: $role, cwd: $cwd}}) RETURN {_SESSION_FIELDS} "
        "ORDER BY s.last_seen_at DESC LIMIT 1",
        {"role": role, "cwd": cwd},
    ).result_set
    return _session(rows[0]) if rows else None


def active_sessions(graph: Graph, *, since: int, include_person: bool = False) -> list[SessionInfo]:
    """Return sessions seen at or after `since`, ordered by role. The person using the CLI
    (role 'person') is not a Claude session, so it is left out unless asked for."""
    rows = graph.ro_query(
        f"MATCH (s:Session) WHERE s.last_seen_at >= $since AND s.role <> 'coordinator' "
        f"AND ($person OR s.role <> 'person') "
        f"RETURN {_SESSION_FIELDS} ORDER BY s.role",
        {"since": since, "person": include_person},
    ).result_set
    return [_session(row) for row in rows]


def count_sessions(graph: Graph, *, role: str, cwd: str, since: int) -> int:
    """Count sessions with this role in this folder seen at or after `since`."""
    rows = graph.ro_query(
        "MATCH (s:Session {role: $role, cwd: $cwd}) WHERE s.last_seen_at >= $since RETURN count(s)",
        {"role": role, "cwd": cwd, "since": since},
    ).result_set
    return int(rows[0][0])


def get_session(graph: Graph, session_id: str) -> SessionInfo | None:
    """Return the session with this id, if it has been registered."""
    rows = graph.ro_query(
        f"MATCH (s:Session {{id: $id}}) RETURN {_SESSION_FIELDS}", {"id": session_id}
    ).result_set
    return _session(rows[0]) if rows else None


def session_for_pid(graph: Graph, *, pid: int, cwd: str) -> SessionInfo | None:
    """Return the newest session of this Claude Code process in this folder."""
    rows = graph.ro_query(
        f"MATCH (s:Session {{pid: $pid, cwd: $cwd}}) RETURN {_SESSION_FIELDS} "
        "ORDER BY s.last_seen_at DESC LIMIT 1",
        {"pid": pid, "cwd": cwd},
    ).result_set
    return _session(rows[0]) if rows else None
