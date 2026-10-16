"""Queries about edits: file changes a session made while working on a request."""

from __future__ import annotations

from falkordb import Graph


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
