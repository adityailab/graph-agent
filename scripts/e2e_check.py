"""Checks for scripts/e2e_scenario.sh: what the deploy session sees after the run.

--reset deletes the scenario's own graph and knowledge graph (and nothing else) first.
"""

from __future__ import annotations

import argparse
import sys

from falkordb import FalkorDB

from handoff.config import Config
from handoff.graph.connection import connect
from handoff.graph.schema import ensure_schema
from handoff.knowledge.startup import knowledge_graph_name
from handoff.mcp.context import ToolContext
from handoff.mcp.read_tools import handoff

# What the deploy session's handoff must contain for the run to count.
EXPECTED = {
    "the frontend request": "Checkout.tsx",
    "the frontend decision": "Decided:",
    "the need, resolved": "(resolved, id",
    "the backend request": "api/orders.py",
}


def reset(config: Config) -> None:
    """Delete this scenario's graphs, so each run starts empty."""
    db = FalkorDB(host=config.host, port=config.port)
    existing = set(db.list_graphs())
    for name in (config.graph_name, knowledge_graph_name(config)):
        if name in existing:
            db.select_graph(name).delete()
    ensure_schema(connect(config))


def check(config: Config, workspace: str) -> int:
    """Print the deploy session's handoff and node counts; 0 if every expected part is there."""
    graph = connect(config)
    text = handoff(ToolContext(role="deploy", cwd=workspace, graph=graph))
    print(text)
    counts = graph.query("MATCH (n) RETURN labels(n)[0], count(n) ORDER BY labels(n)[0]")
    print("\nNodes:", ", ".join(f"{label} {n}" for label, n in counts.result_set))
    missing = [name for name, needle in EXPECTED.items() if needle not in text]
    if missing:
        print(f"\nFAIL: the deploy handoff is missing {', '.join(missing)}.")
        return 1
    print(
        f"\nPASS. Browse it at http://localhost:3000 (graphs {config.graph_name} and "
        f"{knowledge_graph_name(config)})."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()
    config = Config.from_env()
    if args.reset:
        reset(config)
        return 0
    return check(config, args.workspace)


if __name__ == "__main__":
    sys.exit(main())
