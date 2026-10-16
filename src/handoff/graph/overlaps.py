"""Colliding work: the same file changed by more than one session."""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.records import OtherEdit, SharedFile


def recent_edits_by_others(
    graph: Graph, *, path: str, session_id: str, since: int, pid: int | None = None
) -> list[OtherEdit]:
    """Other sessions' latest edits to `path` since `since`, one per session, newest first.

    Sessions of the same Claude Code process (`pid`, the same terminal before /clear)
    do not count as others."""
    rows = graph.ro_query(
        "MATCH (:File {path: $path})<-[:TOUCHED]-(e:Edit)<-[:CAUSED]-(r:Request)"
        "<-[:RECEIVED]-(s:Session) "
        "WHERE s.id <> $sid AND e.at >= $since "
        "AND ($pid IS NULL OR s.pid IS NULL OR s.pid <> $pid) "
        "WITH s, r, e ORDER BY e.at DESC "
        "WITH s, collect([r.text, e.at])[0] AS latest "
        "RETURN s.role, latest[0], latest[1] ORDER BY latest[1] DESC",
        {"path": path, "sid": session_id, "since": since, "pid": pid},
    ).result_set
    return [OtherEdit(role=str(r[0]), request_text=str(r[1]), at=int(r[2])) for r in rows]


def shared_files(graph: Graph, *, since: int) -> list[SharedFile]:
    """Files changed by more than one role since `since`."""
    rows = graph.ro_query(
        "MATCH (f:File)<-[:TOUCHED]-(e:Edit)<-[:CAUSED]-(:Request)<-[:RECEIVED]-(s:Session) "
        "WHERE e.at >= $since "
        "WITH f, collect(DISTINCT s.role) AS roles WHERE size(roles) > 1 "
        "RETURN f.path, roles ORDER BY f.path",
        {"since": since},
    ).result_set
    return [SharedFile(path=str(r[0]), roles=tuple(sorted(str(x) for x in r[1]))) for r in rows]
