"""Queries about topics: the subjects decisions are about."""

from __future__ import annotations

from falkordb import Graph


def nearest_topics(graph: Graph, vector: list[float], *, k: int) -> list[tuple[str, float]]:
    """Topic names nearest to `vector`, with cosine distance (lower is closer)."""
    rows = graph.ro_query(
        "CALL db.idx.vector.queryNodes('Topic', 'embedding', $k, vecf32($v)) "
        "YIELD node, score RETURN node.name, score ORDER BY score",
        {"k": k, "v": vector},
    ).result_set
    return [(str(r[0]), float(r[1])) for r in rows]


def ensure_topic(graph: Graph, name: str, vector: list[float]) -> None:
    """Create the topic if needed and give it an embedding if it has none."""
    graph.query(
        "MERGE (t:Topic {name: $name}) "
        "WITH t WHERE t.embedding IS NULL SET t.embedding = vecf32($v)",
        {"name": name, "v": vector},
    )


def topic_shares_files(graph: Graph, topic: str, request_id: str) -> bool:
    """True when decisions about `topic` came from requests that changed a file this
    request also changed."""
    rows = graph.ro_query(
        "MATCH (:Topic {name: $topic})<-[:ABOUT]-(:Decision)<-[:LED_TO]-(:Request)"
        "-[:CAUSED]->(:Edit)-[:TOUCHED]->(f:File) "
        "MATCH (:Request {id: $rid})-[:CAUSED]->(:Edit)-[:TOUCHED]->(f) "
        "RETURN count(f) > 0",
        {"topic": topic, "rid": request_id},
    ).result_set
    return bool(rows and rows[0][0])
