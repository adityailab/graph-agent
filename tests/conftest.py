from __future__ import annotations

import contextlib
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from falkordb import Graph
from redis.exceptions import ResponseError

from handoff.config import Config
from handoff.graph.connection import connect


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        host="localhost",
        port=6379,
        graph_name=f"test_{uuid.uuid4().hex[:12]}",
        home=tmp_path / "home",
    )


@pytest.fixture
def graph(config: Config) -> Iterator[Graph]:
    g = connect(config)
    yield g
    # ResponseError means the test never wrote anything, so the graph was never created.
    with contextlib.suppress(ResponseError):
        g.delete()
