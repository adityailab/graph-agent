"""What the dashboard shows about the sessions: per-role counts, who talks to whom, and what
one session read of another's work (with the decisions and reasons it learned)."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

from handoff.graph.sessions import active_sessions


@dataclass(frozen=True)
class RoleStats:
    role: str
    last_seen_at: int
    requests: int
    decisions: int
    edits: int
    messages_sent: int
    open_needs: int


@dataclass(frozen=True)
class Flow:
    source: str
    target: str
    kind: str  # message, nudge, digest, read, need
    count: int
    last_at: int


@dataclass(frozen=True)
class Handoff:
    reader: str
    author: str
    request: str
    decisions: tuple[tuple[str, str], ...]  # (decision, reason)
    at: int


_PER_ROLE = {
    "requests": "MATCH (s:Session)-[:RECEIVED]->(x:Request)",
    "decisions": "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(x:Decision)",
    "edits": "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:CAUSED]->(x:Edit)",
    "messages_sent": "MATCH (s:Session)-[:SENT]->(x:Message)",
}

# One query per kind: FalkorDB hangs on a UNION ALL of aggregations.
_FLOWS = (
    "MATCH (s:Session)-[:SENT]->(m:Message) RETURN s.role, m.to_role, m.kind, count(m), max(m.at)",
    "MATCH (a:Session)-[:RECEIVED]->(:Request)-[k:CONSULTED]->(:Request)<-[:RECEIVED]-(o:Session) "
    "RETURN a.role, o.role, 'read', count(k), max(k.at)",
    "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:RAISED]->(n:Need) "
    "RETURN s.role, n.for_role, 'need', count(n), max(n.at)",
)

_HANDOFFS = """
MATCH (a:Session)-[:RECEIVED]->(:Request)-[k:CONSULTED]->(c:Request)<-[:RECEIVED]-(o:Session)
OPTIONAL MATCH (c)-[:LED_TO]->(d:Decision)
RETURN a.role, o.role, c.text, k.at, collect({text: d.text, reason: d.reason})
ORDER BY k.at DESC LIMIT $limit
"""


def _counts(graph: Graph, match: str) -> dict[str, int]:
    rows = graph.ro_query(f"{match} RETURN s.role, count(x)").result_set
    return {str(role): int(n) for role, n in rows}


def role_stats(graph: Graph, *, since: int) -> list[RoleStats]:
    """One row per role with a session active since `since`, newest activity first."""
    counts = {name: _counts(graph, match) for name, match in _PER_ROLE.items()}
    rows = graph.ro_query("MATCH (n:Need {status: 'open'}) RETURN n.for_role, count(n)").result_set
    open_needs = {str(role): int(n) for role, n in rows}
    latest: dict[str, int] = {}
    for session in active_sessions(graph, since=since):
        latest[session.role] = max(latest.get(session.role, 0), session.last_seen_at)
    return [
        RoleStats(
            role,
            seen,
            counts["requests"].get(role, 0),
            counts["decisions"].get(role, 0),
            counts["edits"].get(role, 0),
            counts["messages_sent"].get(role, 0),
            open_needs.get(role, 0),
        )
        for role, seen in sorted(latest.items(), key=lambda item: -item[1])
    ]


def message_flows(graph: Graph) -> list[Flow]:
    """Every (from role, to role, kind) with how often and when last."""
    rows = [row for query in _FLOWS for row in graph.ro_query(query).result_set]
    return [Flow(str(a), str(b), str(k), int(n), int(t or 0)) for a, b, k, n, t in rows]


def handoffs(graph: Graph, *, limit: int) -> list[Handoff]:
    """The newest reads of another session's work, with the decisions made for that work."""
    rows = graph.ro_query(_HANDOFFS, {"limit": limit}).result_set
    return [
        Handoff(
            str(reader),
            str(author),
            str(text),
            tuple((str(d["text"]), str(d["reason"])) for d in found if d["text"] is not None),
            int(at),
        )
        for reader, author, text, at, found in rows
    ]
