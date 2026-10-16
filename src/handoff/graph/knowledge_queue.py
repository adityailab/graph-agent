"""Which requests and decisions still need to go into the knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

MAX_ATTEMPTS = 5

# One query per claim, so two workers never take the same item. A claim makes the item
# ineligible until kg_retry_at, which doubles with each attempt (1, 2, 4, 8, 16 x stale);
# after MAX_ATTEMPTS the item is left out of the knowledge graph.
_ELIGIBLE = (
    "n.kg_at IS NULL AND coalesce(n.kg_attempts, 0) < 5 AND coalesce(n.kg_retry_at, 0) <= $now "
)
_CLAIM = (
    "WITH s, n ORDER BY n.at LIMIT 1 "
    "SET n.kg_retry_at = $now + $stale * [1, 2, 4, 8, 16][coalesce(n.kg_attempts, 0)] "
    "SET n.kg_attempts = coalesce(n.kg_attempts, 0) + 1 "
)
_CLAIM_DECISION = (
    "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(n:Decision) WHERE "
    + _ELIGIBLE
    + _CLAIM
    + "RETURN n.id, s.role, 'The ' + s.role + ' session decided: ' + n.text + "
    "'. Reason: ' + n.reason + '.', 'Decision', size(n.text)"
)
_CLAIM_REQUEST = (
    "MATCH (s:Session)-[:RECEIVED]->(n:Request) WHERE "
    + _ELIGIBLE
    + _CLAIM
    + "RETURN n.id, s.role, 'The ' + s.role + ' session was asked: \"' + n.text + '\"', "
    "'Request', size(n.text)"
)


@dataclass(frozen=True)
class KnowledgeItem:
    id: str
    role: str
    text: str  # what the knowledge graph ingests, naming the role it came from
    label: str  # "Request" or "Decision"
    size: int  # length of the original text


def claim_next(graph: Graph, *, now: int, stale_ms: int) -> KnowledgeItem | None:
    """Claim the oldest eligible decision, else request. None when there is none."""
    for query in (_CLAIM_DECISION, _CLAIM_REQUEST):
        rows = graph.query(query, {"now": now, "stale": stale_ms}).result_set
        if rows:
            r = rows[0]
            return KnowledgeItem(
                id=str(r[0]), role=str(r[1]), text=str(r[2]), label=str(r[3]), size=int(r[4])
            )
    return None


def mark_ingested(graph: Graph, item: KnowledgeItem, *, at: int) -> None:
    """Record that an item is in the knowledge graph (or deliberately left out of it)."""
    label = "Decision" if item.label == "Decision" else "Request"
    graph.query(f"MATCH (n:{label} {{id: $id}}) SET n.kg_at = $at", {"id": item.id, "at": at})
