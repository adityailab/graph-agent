from __future__ import annotations

import socket

import pytest

from handoff.cli.dashboard_cmd import DashboardError, start
from handoff.config import Config


def test_start_serves_on_localhost_and_opens_the_page(config: Config) -> None:
    opened: list[str] = []
    server = start(config, port=0, open_page=opened.append)
    try:
        port = server.server_address[1]
        assert opened == [f"http://127.0.0.1:{port}/"]
    finally:
        server.server_close()


def test_a_page_is_not_opened_when_not_asked_for(config: Config) -> None:
    server = start(config, port=0, open_page=None)
    server.server_close()


def test_a_busy_port_is_explained(config: Config) -> None:
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        with pytest.raises(DashboardError, match="already in use"):
            start(config, port=taken.getsockname()[1], open_page=None)
