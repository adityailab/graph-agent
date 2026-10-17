"""Opening the graph."""

from __future__ import annotations

from falkordb import FalkorDB, Graph
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
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


def probe_server(config: Config) -> str:
    """'falkordb' if FalkorDB answers, 'other' if something else does (plain Redis, or a
    password), 'none' if nothing does."""
    try:  # the client connects as soon as it is created
        db = FalkorDB(
            host=config.host, port=config.port, socket_connect_timeout=1, socket_timeout=2
        )
        db.list_graphs()
    except (RedisConnectionError, RedisTimeoutError, OSError):
        return "none"
    except RedisError:  # unknown command GRAPH.LIST, or authentication required
        return "other"
    return "falkordb"


def server_reachable(config: Config) -> bool:
    """True if FalkorDB answers at the configured address."""
    return probe_server(config) == "falkordb"


def graph_exists(config: Config) -> bool:
    """True if the configured graph exists. Reading a missing graph with GRAPH.QUERY would
    create it, so commands that only look check this first."""
    db = FalkorDB(host=config.host, port=config.port, socket_connect_timeout=1, socket_timeout=5)
    return config.graph_name in db.list_graphs()
