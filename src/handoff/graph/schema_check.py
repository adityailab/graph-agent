"""Reporting schema steps that FalkorDB could not complete."""

from __future__ import annotations

import logging

from falkordb import Graph

log = logging.getLogger(__name__)


def log_failed_constraints(graph: Graph) -> None:
    """Constraints are built in the background; one fails when existing data breaks it,
    e.g. two nodes already share an id. Say so instead of failing silently."""
    for row in graph.ro_query("CALL db.constraints()").result_set:
        kind, label, props, status = str(row[0]), str(row[1]), list(row[2]), str(row[4])
        if status == "FAILED":
            log.warning(
                "%s constraint on %s.%s failed: existing data breaks it",
                kind.lower(),
                label,
                ",".join(str(p) for p in props),
            )
