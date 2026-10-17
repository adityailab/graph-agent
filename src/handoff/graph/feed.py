"""The live stream of what lands in the graph: asked, decided, needs, edits, messages, reads."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph


@dataclass(frozen=True)
class FeedEvent:
    at: int
    role: str
    kind: str  # asked, DECIDED, NEEDS, edited, MESSAGE, QUESTION, STANDIN_ANSWER, READ
    text: str


# One UNION ALL with the same column names in every branch (FalkorDB requires it), inside
# CALL {} so the newest events across all kinds can be ordered and limited together.
_EVENTS = """
CALL {
  MATCH (s:Session)-[:RECEIVED]->(r:Request) WHERE r.at >= $since
  RETURN r.at AS at, s.role AS role, 'asked' AS kind, r.text AS text
  UNION ALL
  MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(d:Decision) WHERE d.at >= $since
  RETURN d.at AS at, s.role AS role, 'DECIDED' AS kind, d.text + ' (why: ' + d.reason + ')' AS text
  UNION ALL
  MATCH (s:Session)-[:RECEIVED]->(:Request)-[:RAISED]->(n:Need) WHERE n.at >= $since
  RETURN n.at AS at, s.role AS role, 'NEEDS' AS kind,
         'from ' + n.for_role + ': ' + n.text + ' [' + n.status + ']' AS text
  UNION ALL
  MATCH (s:Session)-[:RECEIVED]->(:Request)-[:CAUSED]->(e:Edit)-[:TOUCHED]->(f:File)
  WHERE e.at >= $since
  RETURN e.at AS at, s.role AS role, 'edited' AS kind, f.path AS text
  UNION ALL
  MATCH (s:Session)-[:SENT]->(m:Message) WHERE m.at >= $since
  RETURN m.at AS at, s.role AS role, toUpper(m.kind) AS kind,
         'to ' + m.to_role + ': ' + m.text AS text
  UNION ALL
  MATCH (s:Session)-[:RECEIVED]->(:Request)-[k:CONSULTED]->(c:Request)<-[:RECEIVED]-(o:Session)
  WHERE k.at >= $since
  RETURN k.at AS at, s.role AS role, 'READ' AS kind, o.role + ' work: ' + c.text AS text
}
RETURN at, role, kind, text ORDER BY at DESC LIMIT $limit
"""


def recent_events(graph: Graph, *, limit: int, since: int = 0) -> list[FeedEvent]:
    """The newest `limit` events since `since`, oldest first."""
    rows = graph.ro_query(_EVENTS, {"limit": limit, "since": since}).result_set
    return [FeedEvent(int(a or 0), str(r), str(k), str(t)) for a, r, k, t in reversed(rows)]
