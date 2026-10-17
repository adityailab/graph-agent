"""What FalkorDB 4.22 accepts, so Cypher written from scratch works the first time."""

from __future__ import annotations

RULES: tuple[str, ...] = (
    "Always end with LIMIT (25 is plenty): queries are stopped after 1 second.",
    "No EXISTS { } or COUNT { } subqueries: use a pattern predicate, WHERE (a)-[:X]->(b), or "
    "size([(a)-[:X]->() | 1]).",
    "shortestPath works only directed and only in WITH or RETURN. For paths in either "
    "direction: CALL algo.SPpaths({sourceNode: a, targetNode: b, relTypes: "
    "['CAUSED','TOUCHED'], relDirection: 'both', maxLen: 6, pathCount: 1}) YIELD path.",
    "No =~ regular expressions: use string.matchRegEx(text, pattern).",
    "No datetime(): times (at, last_seen_at, started_at) are integer milliseconds since the epoch.",
    "Labels cannot be alternated as (n:A|B): use WHERE n:A OR n:B.",
    "Full-text search: CALL db.idx.fulltext.queryNodes('Decision', 'word') YIELD node, score. "
    "%word% tolerates one typo, word* matches a prefix, | means or.",
    "Read the human fields (text, reason, name, path); ids are opaque and only useful for joining.",
)
