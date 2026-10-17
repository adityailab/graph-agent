"""Queries on the knowledge graph GraphRAG-SDK builds, and the link back to ours.

The knowledge graph's Documents carry our Request and Decision ids; FalkorDB cannot join
across graphs, so the link is made here, one query on each side.
"""

from __future__ import annotations

from falkordb import Graph

from handoff.graph.records import EntityRef, ItemRef
from handoff.graph.search import fulltext_query


def find_entities(kg: Graph, query: str, *, k: int) -> list[EntityRef]:
    """Entities whose name or description matches words of `query`, best first."""
    q = fulltext_query(query)
    if not q:
        return []
    rows = kg.ro_query(
        "CALL db.idx.fulltext.queryNodes('__Entity__', $q) YIELD node, score "
        "RETURN node.name, node.type ORDER BY score DESC LIMIT $k",
        {"q": q, "k": k},
    ).result_set
    return [EntityRef(name=str(r[0]), type=str(r[1] or "")) for r in rows]


def entity_documents(kg: Graph, names: list[str]) -> dict[str, list[str]]:
    """For each entity name, the ids of the documents (our items) that mention it."""
    rows = kg.ro_query(
        "UNWIND $names AS n "
        "MATCH (e:__Entity__ {name: n})-[:MENTIONED_IN]->(:Chunk)<-[:PART_OF]-(d:Document) "
        "RETURN n, collect(DISTINCT d.id)",
        {"names": names},
    ).result_set
    return {str(r[0]): sorted(str(i) for i in r[1]) for r in rows}


def describe_items(graph: Graph, ids: list[str]) -> list[ItemRef]:
    """Our requests and decisions with these ids, with the role behind each, in id order."""
    rows = graph.ro_query(
        "UNWIND $ids AS i "
        "OPTIONAL MATCH (s1:Session)-[:RECEIVED]->(r:Request {id: i}) "
        "OPTIONAL MATCH (s2:Session)-[:RECEIVED]->(:Request)-[:LED_TO]->(d:Decision {id: i}) "
        "WITH i, r, d, coalesce(s1.role, s2.role) AS role WHERE r IS NOT NULL OR d IS NOT NULL "
        "RETURN i, CASE WHEN d IS NULL THEN 'request' ELSE 'decision' END, role, "
        "coalesce(d.text, r.text)",
        {"ids": ids},
    ).result_set
    found = {
        str(r[0]): ItemRef(id=str(r[0]), kind=str(r[1]), role=str(r[2]), text=str(r[3]))
        for r in rows
    }
    return [found[i] for i in ids if i in found]


# GraphRAG-SDK only merges entities with the same name AND type, so "frontend" as a
# Concept and as a Technology stay apart and split the links between sessions. Names that
# differ only in case, spaces or the characters / . - _ ("ProductList" and "product list",
# "dist/" and "dist") are one thing too. This keeps the copy with the longest description and
# moves the others' links onto it.
_MERGE_SAME_NAME = """
MATCH (e:__Entity__)
WITH e, replace(replace(replace(replace(replace(trim(e.name), ' ', ''), '/', ''), '.', ''),
  '-', ''), '_', '') AS folded
WITH toLower(folded) AS key, e
ORDER BY size(coalesce(e.description, '')) DESC
WITH key, collect(e) AS same WHERE size(same) > 1
WITH head(same) AS keep, tail(same) AS dups
UNWIND dups AS dup
CALL {
  WITH keep, dup
  MATCH (dup)-[r:RELATES]->(t) WHERE t <> keep
  MERGE (keep)-[n:RELATES {rel_type: coalesce(r.rel_type, '')}]->(t)
  ON CREATE SET n = properties(r)
  ON MATCH SET n.source_chunk_ids = coalesce(n.source_chunk_ids, []) +
    [x IN coalesce(r.source_chunk_ids, []) WHERE NOT x IN coalesce(n.source_chunk_ids, [])]
  RETURN count(*) AS moved_out
}
CALL {
  WITH keep, dup
  MATCH (s)-[r:RELATES]->(dup) WHERE s <> keep
  MERGE (s)-[n:RELATES {rel_type: coalesce(r.rel_type, '')}]->(keep)
  ON CREATE SET n = properties(r)
  ON MATCH SET n.source_chunk_ids = coalesce(n.source_chunk_ids, []) +
    [x IN coalesce(r.source_chunk_ids, []) WHERE NOT x IN coalesce(n.source_chunk_ids, [])]
  RETURN count(*) AS moved_in
}
CALL {
  WITH keep, dup
  MATCH (dup)-[:MENTIONED_IN]->(c)
  MERGE (keep)-[:MENTIONED_IN]->(c)
  RETURN count(*) AS mentions
}
DETACH DELETE dup
RETURN count(dup)
"""


def merge_same_name_entities(kg: Graph) -> int:
    """Merge knowledge-graph entities whose names match once case, spaces and / . - _ are
    ignored, whatever their type; return how many duplicates were removed."""
    return int(kg.query(_MERGE_SAME_NAME).result_set[0][0])
