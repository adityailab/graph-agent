"""Indexes and constraints: lookups, uniqueness, full-text search and vector search."""

from __future__ import annotations

import logging
from collections.abc import Callable

from falkordb import Graph
from redis.exceptions import ResponseError

from handoff.graph.schema_check import log_failed_constraints
from handoff.graph.udf import load_udfs

log = logging.getLogger(__name__)

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
    ("Insight", "kind"),
    ("Action", "key"),
    ("Convention", "id"),
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
    ("Action", "key"),
    ("Convention", "id"),
)

FULLTEXT: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Request", ("text",)),
    ("Decision", ("text", "reason")),
    ("Need", ("text",)),
    ("Message", ("text",)),
    ("Convention", ("text", "reason")),
)

VECTOR: tuple[tuple[str, str], ...] = (
    ("Decision", "embedding"),
    ("Topic", "embedding"),
)


def _create(make: Callable[..., object], *args: object, **kwargs: object) -> None:
    try:
        make(*args, **kwargs)
    except ResponseError as exc:
        # "already" means it exists. Anything else is logged, not raised: every item here
        # is an index or a constraint, and the graph works (more slowly) without one.
        if "already" not in str(exc).lower():
            log.warning("schema step %s%s failed: %s", make.__name__, args, exc)


def ensure_schema(graph: Graph) -> None:
    """Create any missing index or constraint. Existing ones are left alone. Never raises
    for a schema step; failures, including constraints broken by existing data, are logged."""
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
    # Constraints are built asynchronously, so a failure shows on the next call at the latest.
    log_failed_constraints(graph)
    load_udfs(graph)  # handoff.overlap; never raises
