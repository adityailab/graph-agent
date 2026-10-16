"""`handoff-knowledge`: run the knowledge worker on its own, outside any session.

`handoff-knowledge` keeps running and ingests new work as it arrives;
`handoff-knowledge --once` ingests everything pending and exits.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from handoff.config import Config
from handoff.embed import FastEmbedder
from handoff.knowledge.startup import start_knowledge
from handoff.models.choose import model_from_env


def main(argv: list[str] | None = None) -> int:
    """Run the worker in the foreground. Returns the exit code."""
    parser = argparse.ArgumentParser(prog="handoff-knowledge")
    parser.add_argument("--once", action="store_true", help="ingest what is pending, then exit")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    config = Config.from_env()
    env = {**os.environ, "HANDOFF_KNOWLEDGE": "on"}
    knowledge = start_knowledge(
        config,
        model_from_env(os.environ),
        FastEmbedder(cache_dir=config.home / "models"),
        env=env,
        background=False,
    )
    if knowledge is None:
        print("The database is unreachable; nothing to do.", file=sys.stderr)
        return 1
    if args.once:
        print(f"Ingested {knowledge.worker.drain()} items into {config.graph_name}_kg.")
        return 0
    knowledge.worker.run()
    return 0
