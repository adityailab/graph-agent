"""Indexes for every property the code looks nodes up by."""

from __future__ import annotations

from falkordb import Graph
from redis.exceptions import ResponseError

INDEXED: tuple[tuple[str, str], ...] = (
    ("Session", "id"),
    ("Session", "role"),
    ("Request", "id"),
    ("Edit", "id"),
    ("File", "path"),
    ("Decision", "id"),
    ("Need", "id"),
    ("Topic", "name"),
    ("Message", "id"),
)


def ensure_schema(graph: Graph) -> None:
    """Create any missing range indexes. Existing ones are left alone."""
    for label, prop in INDEXED:
        try:
            graph.create_node_range_index(label, prop)
        except ResponseError as exc:
            # FalkorDB refuses to create an index that already exists.
            if "already indexed" not in str(exc).lower():
                raise
