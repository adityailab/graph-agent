"""A small local web server: the dashboard page plus the one JSON endpoint it polls."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from handoff.config import Config
from handoff.dashboard.state import snapshot
from handoff.ids import now_ms

log = logging.getLogger(__name__)

STATIC = Path(__file__).parent / "static"
WINDOW_MS = 24 * 60 * 60_000
_TYPES = {  # file suffix -> content type; only these files in static/ are served
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}
# Everything is served from this origin; nothing else may load or be framed.
_SECURITY = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}


def make_server(
    config: Config, *, port: int, clock: Callable[[], int] = now_ms
) -> ThreadingHTTPServer:
    """A server on localhost only (port 0 picks a free one). Call serve_forever() to run it."""

    allowed_hosts: set[str] = set()  # filled in once the port is known

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            for name, value in _SECURITY.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _host_ok(self) -> bool:
            return self.headers.get("Host", "") in allowed_hosts

        def do_GET(self) -> None:
            if not self._host_ok():
                self._send(403, b"forbidden", "text/plain")
            elif self.path == "/api/state":
                state: dict[str, Any] = snapshot(config, now=clock(), window_ms=WINDOW_MS)
                self._send(200, json.dumps(state).encode(), "application/json")
            else:
                name = self.path.split("?")[0].lstrip("/") or "index.html"
                served = {f.name: f for f in STATIC.iterdir() if f.suffix in _TYPES}
                if name in served:  # exact file names only, so no path can climb out
                    self._send(200, served[name].read_bytes(), _TYPES[served[name].suffix])
                else:
                    self._send(404, b"not found", "text/plain")

        def log_message(self, format: str, *args: Any) -> None:
            log.debug(format, *args)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    allowed_hosts.update({f"127.0.0.1:{server.server_port}", f"localhost:{server.server_port}"})
    return server
