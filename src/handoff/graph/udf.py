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


_FUNCTIONS = ["overlap"]  # what _SOURCE registers; a different set means an outdated library


def _text(value: object) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def _installed_functions(graph: Graph) -> list[str] | None:
    """The functions of our library as the server has it, or None if it is not loaded.
    Matches the library name exactly: 'handoff_other' is not ours."""
    for entry in graph.execute_command("GRAPH.UDF", "LIST"):
        info = {_text(k): v for k, v in zip(entry[::2], entry[1::2], strict=False)}
        if _text(info.get("library_name")) == UDF_LIBRARY:
            return sorted(_text(f) for f in info.get("functions", []))
    return None


def load_udfs(graph: Graph) -> bool:
    """Make sure the current handoff.overlap exists on the server (loading or replacing the
    library when it is missing or outdated). False if UDFs are unavailable."""
    try:
        if _installed_functions(graph) == _FUNCTIONS:
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
