"""Checks for scripts/e2e_scenario.sh: what the deploy session sees after the run.

--reset deletes the named graph, its knowledge graph and GraphRAG's ontology graph, and
nothing else; the graph must always be named (--graph), so a default graph holding real
history can never be deleted by accident.
"""

from __future__ import annotations

import argparse
import sys

from falkordb import FalkorDB

from handoff.config import Config
from handoff.format import render_handoff, select_requests
from handoff.graph.connection import connect
from handoff.graph.history import handoff_requests
from handoff.graph.schema import ensure_schema
from handoff.knowledge.startup import knowledge_graph_name

# What the deploy session's handoff must contain for the run to count.
EXPECTED = {
    "the frontend request": "Checkout.tsx",
    "the frontend decision": "Decided:",
    "the need, resolved": "(resolved, id",
    "the backend request": "api/orders.py",
}

# Communication the graph must show, as (what, Cypher count query).
EXPECTED_EDGES = {
    "a message delivered to a session": (
        "MATCH (:Message)-[:DELIVERED_TO]->(:Session) RETURN count(*)"
    ),
    "a stand-in answer citing its sources": (
        "MATCH (:Message {kind: 'standin_answer'})-[:CITES]->() RETURN count(*)"
    ),
    "a request that consulted another session's work": (
        "MATCH (:Request)-[:CONSULTED]->(:Request) RETURN count(*)"
    ),
}


def reset(config: Config) -> None:
    """Delete this scenario's graphs, so each run starts empty."""
    db = FalkorDB(host=config.host, port=config.port)
    existing = set(db.list_graphs())
    kg = knowledge_graph_name(config)
    for name in (config.graph_name, kg, f"{kg}__ontology"):
        if name in existing:
            db.select_graph(name).delete()
    ensure_schema(connect(config))


def check(config: Config, workspace: str) -> int:
    """Print the deploy session's handoff and node counts; 0 if every expected part is there."""
    if config.graph_name not in FalkorDB(host=config.host, port=config.port).list_graphs():
        print(f"No graph named {config.graph_name}; run scripts/e2e_scenario.sh first.")
        return 1
    graph = connect(config)
    # Count what the sessions did before anything here touches the graph, and render the
    # handoff without the tool, which would record CONSULTED edges of its own.
    missing = [
        name for name, query in EXPECTED_EDGES.items() if graph.query(query).result_set[0][0] == 0
    ]
    text = render_handoff(select_requests(handoff_requests(graph, role=None, since=0), 10))
    print(text)
    counts = graph.query("MATCH (n) RETURN labels(n)[0], count(n) ORDER BY labels(n)[0]")
    print("\nNodes:", ", ".join(f"{label} {n}" for label, n in counts.result_set))
    missing += [name for name, needle in EXPECTED.items() if needle not in text]
    if missing:
        print(f"\nFAIL: missing {', '.join(missing)}.")
        return 1
    print(
        f"\nPASS. Browse it at http://localhost:3000 (graphs {config.graph_name} and "
        f"{knowledge_graph_name(config)})."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", required=True, help="the scenario's graph name")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()
    env = Config.from_env()
    config = Config(env.host, env.port, args.graph, env.home)
    if args.reset:
        reset(config)
        return 0
    return check(config, args.workspace)


if __name__ == "__main__":
    sys.exit(main())
