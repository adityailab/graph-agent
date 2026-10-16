"""Indexes and constraints: lookups, uniqueness, full-text search and vector search."""

from __future__ import annotations

from collections.abc import Callable

from falkordb import Graph
from redis.exceptions import ResponseError

EMBED_DIM = 384  # BAAI/bge-small-en-v1.5, see handoff.embed

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
    ("Message", "to_role"),
    ("Need", "for_role"),
)

# Each needs the matching range index above first.
UNIQUE: tuple[tuple[str, str], ...] = (
    ("Session", "id"),
    ("Request", "id"),
    ("Edit", "id"),
    ("File", "path"),
    ("Decision", "id"),
    ("Need", "id"),
    ("Topic", "name"),
    ("Message", "id"),
)

FULLTEXT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Request", ("text",)),
    ("Decision", ("text", "reason")),
    ("Need", ("text",)),
    ("Message", ("text",)),
)

VECTOR: tuple[tuple[str, str], ...] = (
    ("Decision", "embedding"),
    ("Topic", "embedding"),
)


def _create(make: Callable[..., object], *args: object, **kwargs: object) -> None:
    try:
        make(*args, **kwargs)
    except ResponseError as exc:
        # FalkorDB refuses to create an index or constraint that already exists.
        if "already" not in str(exc).lower():
            raise


def ensure_schema(graph: Graph) -> None:
    """Create any missing index or constraint. Existing ones are left alone."""
    for label, prop in INDEXED:
        _create(graph.create_node_range_index, label, prop)
    for label, prop in UNIQUE:
        _create(graph.create_node_unique_constraint, label, prop)
    for label, props in FULLTEXT:
        _create(graph.create_node_fulltext_index, label, *props)
    for label, prop in VECTOR:
        _create(
            graph.create_node_vector_index, label, prop, dim=EMBED_DIM, similarity_function="cosine"
        )
