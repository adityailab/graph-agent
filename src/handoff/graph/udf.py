"""handoff's FalkorDB user-defined function: JavaScript that runs inside the database.

handoff.overlap(a, b) is the Jaccard share of two lists (e.g. the files two requests
changed). UDF libraries belong to the whole server, not a graph, so it is loaded once
and only when missing.
"""

from __future__ import annotations

import logging

from falkordb import Graph
from redis.exceptions import ResponseError

log = logging.getLogger(__name__)

UDF_LIBRARY = "handoff"
_SOURCE = """
function overlap(a, b) {
  const x = new Set(a), y = new Set(b);
  if (x.size === 0 && y.size === 0) return 0.0;
  let common = 0;
  for (const v of x) if (y.has(v)) common++;
  return common / (x.size + y.size - common);
}
falkor.register('overlap', overlap);
"""


def load_udfs(graph: Graph) -> bool:
    """Make sure handoff.overlap exists on the server. False if UDFs are unavailable."""
    try:
        if UDF_LIBRARY in str(graph.execute_command("GRAPH.UDF", "LIST")):
            return True
        graph.execute_command("GRAPH.UDF", "LOAD", "REPLACE", UDF_LIBRARY, _SOURCE)
    except ResponseError as exc:  # an older FalkorDB without UDFs: handoff works without
        log.warning("FalkorDB UDFs unavailable: %s", exc)
        return False
    return True


def file_overlap(graph: Graph, a: str, b: str) -> float | None:
    """The share of files two requests both changed, or None if the UDF is unavailable."""
    try:
        rows = graph.ro_query(
            "MATCH (a:Request {id: $a}), (b:Request {id: $b}) "
            # Distinct variable names: in FalkorDB 4.22 a second pattern comprehension that
            # reuses the first one's variable silently returns [].
            "RETURN handoff.overlap([(a)-[:CAUSED]->()-[:TOUCHED]->(fa) | fa.path], "
            "[(b)-[:CAUSED]->()-[:TOUCHED]->(fb) | fb.path])",
            {"a": a, "b": b},
        ).result_set
    except ResponseError:  # the function is not loaded
        return None
    return float(rows[0][0]) if rows else None
