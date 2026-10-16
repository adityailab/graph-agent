"""Opening the graph."""

from __future__ import annotations

from falkordb import FalkorDB, Graph

from handoff.config import Config


def connect(config: Config) -> Graph:
    """Return a handle to the configured graph.

    Short timeouts keep hooks fast when the database is down; they fall back to
    the replay file instead of waiting.
    """
    db = FalkorDB(
        host=config.host,
        port=config.port,
        socket_connect_timeout=1,
        socket_timeout=5,
    )
    return db.select_graph(config.graph_name)
