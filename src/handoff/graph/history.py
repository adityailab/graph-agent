"""The handoff query: what sessions were asked, what they decided, changed and need."""

from __future__ import annotations

from typing import Any

from falkordb import Graph

from handoff.graph.records import NeedView, RequestView, decision_views

_HANDOFF_QUERY = (
    "MATCH (s:Session)-[:RECEIVED]->(r:Request) "
    "WHERE ($role IS NULL OR s.role = $role) AND r.at >= $since "
    "OPTIONAL MATCH (r)-[:CAUSED]->(:Edit)-[:TOUCHED]->(f:File) "
    "WITH s, r, collect(DISTINCT f.path) AS files "
    "OPTIONAL MATCH (r)-[:LED_TO]->(d:Decision) "
    "WITH s, r, files, collect(DISTINCT [d.id, d.text, d.reason]) AS decisions "
    "OPTIONAL MATCH (r)-[:RAISED]->(n:Need) "
    "RETURN s.role, r.id, r.seq, r.text, r.at, files, decisions, "
    "collect(DISTINCT [n.id, n.text, n.for_role, n.status]) AS needs "
    "ORDER BY r.at"
)


def _needs(raw: list[list[Any]]) -> tuple[NeedView, ...]:
    # An OPTIONAL MATCH with no match collects one list of nulls; drop it.
    return tuple(
        NeedView(id=str(i), text=str(t), for_role=str(r), status=str(st))
        for i, t, r, st in raw
        if i is not None
    )


def _request_view(row: list[Any]) -> RequestView:
    return RequestView(
        role=str(row[0]),
        id=str(row[1]),
        seq=int(row[2]),
        text=str(row[3]),
        at=int(row[4]),
        files=tuple(sorted(str(p) for p in row[5])),
        decisions=decision_views(row[6]),
        needs=_needs(row[7]),
    )


def handoff_requests(graph: Graph, *, role: str | None, since: int) -> list[RequestView]:
    """Return requests made at or after `since`, oldest first, with what each led to.

    `role=None` covers every role.
    """
    rows = graph.ro_query(_HANDOFF_QUERY, {"role": role, "since": since}).result_set
    return [_request_view(row) for row in rows]
