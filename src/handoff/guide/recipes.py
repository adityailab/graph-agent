"""Cypher a session can run as written (literal example values to replace). Each one is
tested read-only against a seeded graph, so none can quietly stop working."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recipe:
    name: str
    graph: str  # "work" or "kg"
    cypher: str


RECIPES: tuple[Recipe, ...] = (
    Recipe(
        "who read whose work",
        "work",
        "MATCH "
        "(a:Session)-[:RECEIVED]->(:Request)-[k:CONSULTED]->(c:Request)<-[:RECEIVED]-(b:Session) "
        "RETURN a.role AS reader, b.role AS author, c.name AS work, k.at AS at ORDER BY at DESC "
        "LIMIT 25",
    ),
    Recipe(
        "open needs between roles",
        "work",
        "MATCH (s:Session)-[:RECEIVED]->(:Request)-[:RAISED]->(n:Need {status: 'open'}) "
        "RETURN s.role AS asked_by, n.for_role AS asked_of, n.text AS need LIMIT 25",
    ),
    Recipe(
        "decisions behind a file (replace 'Card')",
        "work",
        "MATCH (f:File)<-[:TOUCHED]-(:Edit)<-[:CAUSED]-(r:Request)-[:LED_TO]->(d:Decision) "
        "WHERE f.path CONTAINS 'Card' RETURN f.path, d.text, d.reason LIMIT 25",
    ),
    Recipe(
        "search decisions, typo-tolerant",
        "work",
        "CALL db.idx.fulltext.queryNodes('Decision', '%paise%') YIELD node, score "
        "RETURN node.text, node.reason, score ORDER BY score DESC LIMIT 10",
    ),
    Recipe(
        "decisions similar in meaning to one decision",
        "work",
        "MATCH (d:Decision) WHERE d.embedding IS NOT NULL WITH d LIMIT 1 "
        "CALL db.idx.vector.queryNodes('Decision', 'embedding', 5, d.embedding) YIELD node, score "
        "RETURN d.text AS decision, node.text AS similar, score LIMIT 5",
    ),
    Recipe(
        "most-read requests (PageRank over CONSULTED)",
        "work",
        "CALL algo.pageRank('Request', 'CONSULTED') YIELD node, score "
        "RETURN node.name, score ORDER BY score DESC LIMIT 5",
    ),
    Recipe(
        "requests that relay reading (betweenness; a sampled estimate, so pass a seed)",
        "work",
        "CALL algo.betweenness({nodeLabels: ['Request'], relationshipTypes: ['CONSULTED'], "
        "samplingSize: 10000, samplingSeed: 42}) "
        "YIELD node, score WITH node, score WHERE score > 0 "
        "RETURN node.name, score ORDER BY score DESC LIMIT 5",
    ),
    Recipe(
        "clusters of edits sharing files (connected components)",
        "work",
        "CALL algo.WCC({nodeLabels: ['Edit', 'File'], relationshipTypes: ['TOUCHED']}) "
        "YIELD node, componentId WITH componentId, collect(node.name) AS members "
        "WHERE size(members) > 2 RETURN componentId, members LIMIT 5",
    ),
    Recipe(
        "one role's requests in order (replace 'frontend')",
        "work",
        "MATCH (s:Session {role: 'frontend'})-[:RECEIVED]->(r:Request) "
        "RETURN r.seq, r.text, r.at ORDER BY r.at LIMIT 25",
    ),
    Recipe(
        "where a concept was mentioned (replace 'avatar')",
        "kg",
        "MATCH (e:__Entity__)-[:MENTIONED_IN]->(:Chunk)<-[:PART_OF]-(d:Document) "
        "WHERE toLower(e.name) CONTAINS 'avatar' "
        "RETURN e.name, collect(DISTINCT d.id) AS request_or_decision_ids LIMIT 10",
    ),
    Recipe(
        "how a concept relates to others (replace 'avatar')",
        "kg",
        "MATCH (a:__Entity__)-[r:RELATES]->(b:__Entity__) WHERE toLower(a.name) CONTAINS 'avatar' "
        "RETURN a.name, r.rel_type, b.name, r.fact LIMIT 25",
    ),
)
