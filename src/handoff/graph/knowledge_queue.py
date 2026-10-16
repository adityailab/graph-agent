"""Which requests and decisions still need to go into the knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

# Each claim is one query, so two workers can never take the same item. A claim older
# than `stale_ms` belongs to a worker that died, and is taken again.
_CLAIM_DECISION = (
    "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(n:Decision) "
    "WHERE n.kg_at IS NULL AND (n.kg_claim IS NULL OR n.kg_claim < $stale) "
    "WITH s, n ORDER BY n.at LIMIT 1 "
    "SET n.kg_claim = $now "
    "RETURN n.id, s.role, 'The ' + s.role + ' session decided: ' + n.text + "
    "'. Reason: ' + n.reason + '.'"
)
_CLAIM_REQUEST = (
    "MATCH (s:Session)-[:RECEIVED]->(n:Request) "
    "WHERE n.kg_at IS NULL AND (n.kg_claim IS NULL OR n.kg_claim < $stale) "
    "WITH s, n ORDER BY n.at LIMIT 1 "
    "SET n.kg_claim = $now "
    "RETURN n.id, s.role, 'The ' + s.role + ' session was asked: \"' + n.text + '\"'"
)


@dataclass(frozen=True)
class KnowledgeItem:
    id: str
    role: str
    text: str  # what the knowledge graph ingests, naming the role it came from


def claim_next(graph: Graph, *, now: int, stale_ms: int) -> KnowledgeItem | None:
    """Claim the oldest un-ingested decision, else request. None when there is none."""
    for query in (_CLAIM_DECISION, _CLAIM_REQUEST):
        rows = graph.query(query, {"now": now, "stale": now - stale_ms}).result_set
        if rows:
            return KnowledgeItem(id=str(rows[0][0]), role=str(rows[0][1]), text=str(rows[0][2]))
    return None


def mark_ingested(graph: Graph, item_id: str, *, at: int) -> None:
    """Record that an item is in the knowledge graph."""
    graph.query(
        "MATCH (n) WHERE (n:Request OR n:Decision) AND n.id = $id SET n.kg_at = $at",
        {"id": item_id, "at": at},
    )
