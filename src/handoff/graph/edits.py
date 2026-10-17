"""Queries about edits: file changes a session made while working on a request."""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.records import WhyRow, decision_views


def add_edit(
    graph: Graph,
    *,
    request_id: str,
    edit_id: str,
    tool: str,
    path: str,
    summary: str,
    at: int,
) -> bool:
    """Attach an edit of `path` to the request that caused it.

    Returns False when the request is unknown. Calling again with the same edit_id
    changes nothing, which makes replaying the local file safe.
    """
    rows = graph.query(
        "MATCH (r:Request {id: $rid}) "
        "MERGE (e:Edit {id: $eid}) "
        "ON CREATE SET e.tool = $tool, e.summary = $summary, e.at = $at, "
        "e.name = $tool + ' ' + $path "
        "MERGE (r)-[:CAUSED]->(e) "
        "MERGE (f:File {path: $path}) ON CREATE SET f.name = $path "
        "MERGE (e)-[:TOUCHED]->(f) "
        "RETURN e.id",
        {
            "rid": request_id,
            "eid": edit_id,
            "tool": tool,
            "path": path,
            "summary": summary,
            "at": at,
        },
    ).result_set
    return bool(rows)


def why_file(graph: Graph, path: str, limit: int = 20) -> list[WhyRow]:
    """Return one row per edit to `path`, newest first, with its request and decisions."""
    rows = graph.ro_query(
        "MATCH (f:File {path: $path})<-[:TOUCHED]-(e:Edit)<-[:CAUSED]-(r:Request)"
        "<-[:RECEIVED]-(s:Session) "
        "OPTIONAL MATCH (r)-[:LED_TO]->(d:Decision) "
        "WITH s, r, e, collect(DISTINCT [d.id, d.text, d.reason]) AS decisions "
        "RETURN s.role, r.text, decisions, e.summary, e.at "
        "ORDER BY e.at DESC LIMIT $limit",
        {"path": path, "limit": limit},
    ).result_set
    return [
        WhyRow(
            role=str(row[0]),
            request_text=str(row[1]),
            decisions=decision_views(row[2]),
            edit_summary=str(row[3]),
            at=int(row[4]),
        )
        for row in rows
    ]
