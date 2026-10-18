"""The dashboard's command field: the person messages a session or raises a need for one."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from handoff.config import Config, normalise_role
from handoff.graph.connection import connect
from handoff.graph.schema import ensure_schema
from handoff.person import raise_need, send_message

MAX_BODY = 8192
MAX_TEXT = 2000
_KINDS = ("msg", "need")


def _read(body: bytes) -> tuple[str, str, str] | None:
    """(kind, role, text) from the request body, or None when it is not a clear command."""
    try:
        sent = json.loads(body[:MAX_BODY])
        kind, to, text = sent.get("kind"), sent.get("to"), sent.get("text")
    except (ValueError, AttributeError):
        return None
    if kind not in _KINDS or not isinstance(to, str) or not isinstance(text, str):
        return None
    to, text = to.strip(), text.strip()
    if not to or not text or len(text) > MAX_TEXT:
        return None
    return kind, normalise_role(to), text


def run_command(
    body: bytes, content_type: str, config: Config, folder: Path, *, now: int
) -> tuple[int, dict[str, Any]]:
    """Carry out one command; the reply is one line the page shows under the field."""
    if content_type.split(";")[0].strip() != "application/json":
        return 415, {"error": "send JSON"}  # a form post from another page cannot be JSON
    command = _read(body)
    if command is None:
        return 400, {"error": "say: msg <session> <text>  or  need <session> <text>"}
    kind, role, text = command
    graph = connect(config)
    ensure_schema(graph)
    if kind == "msg":
        known = send_message(graph, folder, role, text, at=now)
        later = f" No session has the role {role} yet; it will get this when one starts."
        return 200, {"reply": f"Sent to {role}." + ("" if known else later)}
    raise_need(graph, folder, role, text, at=now)
    return 200, {"reply": f"Need raised for {role}; it shows as open until someone resolves it."}
