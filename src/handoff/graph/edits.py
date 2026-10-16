"""Queries about edits: file changes a session made while working on a request."""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.records import WhyRow


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
        "ON CREATE SET e.tool = $tool, e.summary = $summary, e.at = $at "
        "MERGE (r)-[:CAUSED]->(e) "
        "MERGE (f:File {path: $path}) "
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
    """Return the requests and decisions behind edits to `path`, newest edit first."""
    rows = graph.ro_query(
        "MATCH (f:File {path: $path})<-[:TOUCHED]-(e:Edit)<-[:CAUSED]-(r:Request)"
        "<-[:RECEIVED]-(s:Session) "
        "OPTIONAL MATCH (r)-[:LED_TO]->(d:Decision) "
        "RETURN s.role, r.text, d.text, d.reason, e.summary, e.at "
        "ORDER BY e.at DESC LIMIT $limit",
        {"path": path, "limit": limit},
    ).result_set
    return [
        WhyRow(
            role=str(row[0]),
            request_text=str(row[1]),
            decision_text=None if row[2] is None else str(row[2]),
            decision_reason=None if row[3] is None else str(row[3]),
            edit_summary=str(row[4]),
            at=int(row[5]),
        )
        for row in rows
    ]
