from __future__ import annotations

import threading
import urllib.request
from collections.abc import Iterator

import pytest

from handoff.config import Config
from handoff.dashboard.server import make_server


@pytest.fixture
def base(config: Config) -> Iterator[str]:
    server = make_server(config, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_the_logo_is_served_as_an_image(base: str) -> None:
    with urllib.request.urlopen(base + "/logo.svg", timeout=5) as response:
        assert response.headers["Content-Type"].startswith("image/svg+xml")
        assert b"<svg" in response.read()


def test_the_page_names_the_logo_as_its_icon(base: str) -> None:
    with urllib.request.urlopen(base + "/", timeout=5) as response:
        assert b'rel="icon"' in response.read()


def test_the_server_can_queue_a_page_load_worth_of_connections(config: Config) -> None:
    # A page asks for about twenty files at once; the default queue of 5 resets the rest.
    server = make_server(config, port=0)
    try:
        assert server.request_queue_size >= 64
    finally:
        server.server_close()
