"""Opening the graph."""

from __future__ import annotations

from falkordb import FalkorDB, Graph
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

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


def ping(graph: Graph) -> None:
    """Raise a redis error if the database cannot be reached."""
    graph.ro_query("RETURN 1")


def server_reachable(config: Config) -> bool:
    """True if a FalkorDB (Redis) server answers at the configured address."""
    try:  # the client connects as soon as it is created
        db = FalkorDB(
            host=config.host, port=config.port, socket_connect_timeout=1, socket_timeout=2
        )
        return bool(db.connection.ping())
    except (RedisConnectionError, RedisTimeoutError, OSError):
        return False
