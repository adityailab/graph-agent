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
from handoff.models.choose import model_from_env

_LIBRARY_LOGGERS = ("graphrag_sdk", "httpx2", "httpx", "anthropic")


def configure_logging(*, quiet: bool) -> None:
    """Log to the terminal. Quiet mode hides the libraries' step-by-step chatter (GraphRAG
    pipeline steps, HTTP requests, harmless "already indexed" errors) and keeps our own
    messages and warnings."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    for name in _LIBRARY_LOGGERS:
        logging.getLogger(name).setLevel(logging.CRITICAL if quiet else logging.NOTSET)


def main(argv: list[str] | None = None) -> int:
    """Run the worker in the foreground. Returns the exit code."""
    parser = argparse.ArgumentParser(prog="handoff-knowledge")
    parser.add_argument("--once", action="store_true", help="ingest what is pending, then exit")
    parser.add_argument("--quiet", action="store_true", help="hide library log lines")
    args = parser.parse_args(argv)
    try:
        from handoff.knowledge.startup import start_knowledge
    except ImportError:
        print("The knowledge extra is not installed: uv sync --extra knowledge", file=sys.stderr)
        return 1
    configure_logging(quiet=args.quiet)
    config = Config.from_env()
    env = {**os.environ, "HANDOFF_KNOWLEDGE": "on"}
    ingest_name = os.environ.get("HANDOFF_KNOWLEDGE_MODEL")
    model_env = {**os.environ, "HANDOFF_MODEL_NAME": ingest_name} if ingest_name else os.environ
    knowledge = start_knowledge(
        config,
        model_from_env(model_env),
        FastEmbedder(cache_dir=config.home / "models"),
        env=env,
        background=False,
    )
    if knowledge is None:
        print("The database is unreachable; nothing to do.", file=sys.stderr)
        return 1
    if not knowledge.worker.try_lead():
        print("Another knowledge worker is already running for this graph.", file=sys.stderr)
        return 1
    if args.once:
        print(f"Handled {knowledge.worker.drain()} items for {config.graph_name}_kg.")
        return 0
    knowledge.worker.run()
    return 0
