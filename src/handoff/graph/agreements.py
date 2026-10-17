"""Agreement between roles: two decisions that say the same thing, made by different sessions."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

from handoff.graph.search import similar_decisions

AGREE = 0.20  # cosine distance: measured near-duplicate decisions were 0.14-0.18 apart
NEIGHBOURS = 6

_ROLES = """
UNWIND $ids AS i
MATCH (s:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(d:Decision {id: i})
RETURN d.id, s.role, d.text
"""
_LINK = """
MATCH (new:Decision {id: $new}), (old:Decision {id: $old})
MERGE (new)-[r:AGREES_WITH]->(old)
ON CREATE SET r.at = $at, r.distance = $distance
"""


@dataclass(frozen=True)
class Agreement:
    decision_id: str
    role: str
    text: str


def link_agreements(
    graph: Graph, decision_id: str, vector: list[float], *, role: str, at: int
) -> list[Agreement]:
    """Link `decision_id` to each near-identical decision another role made, and return them.
    One edge per pair, so linking again changes nothing."""
    near = {
        d: dist
        for d, dist in similar_decisions(graph, vector, k=NEIGHBOURS)
        if d != decision_id and dist <= AGREE
    }
    if not near:
        return []
    rows = graph.ro_query(_ROLES, {"ids": list(near)}).result_set
    agreed = [Agreement(str(d), str(r), str(t)) for d, r, t in rows if str(r) != role]
    for a in agreed:
        graph.query(
            _LINK,
            {"new": decision_id, "old": a.decision_id, "at": at, "distance": near[a.decision_id]},
        )
    return sorted(agreed, key=lambda a: near[a.decision_id])
