"""How a headless demo ends: build the knowledge graph, then check what deploy can see."""

from __future__ import annotations

import os

from handoff.config import Config, knowledge_graph_name
from handoff.demo.check import check_graph


def build_knowledge(config: Config) -> None:
    """Ingest what happened into the knowledge graph (skipped without the extra)."""
    try:
        from handoff.knowledge.cli import main as knowledge_main
    except ImportError:
        print("(knowledge graph skipped: install the 'knowledge' extra)")
        return
    os.environ["HANDOFF_GRAPH"] = config.graph_name
    print("\n== building the knowledge graph (one model call per item)", flush=True)
    knowledge_main(["--once", "--quiet"])


def report(config: Config) -> int:
    """Print what the deploy session can see and PASS or what is missing; the exit code."""
    text, missing = check_graph(config)
    print(f"\n== what the deploy session can see\n{text}")
    if missing:
        print(f"\nFAIL: missing {', '.join(missing)}.")
        return 1
    print(
        f"\nPASS. Browse it at http://localhost:3000: graphs {config.graph_name} and "
        f"{knowledge_graph_name(config)}."
    )
    return 0
