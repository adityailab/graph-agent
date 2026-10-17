"""The dashboard's ask box: one question in, Claude's answer from the graphs and its Cypher out."""

from __future__ import annotations

import json
import subprocess
import threading
from collections.abc import Callable
from typing import Any

from handoff.config import Config

Asker = Callable[[str, Config], tuple[str, list[str]]]
MAX_BODY = 4096
MAX_QUESTION = 500
_busy = threading.Lock()  # one question at a time: each one spends the person's Claude plan


def handle_ask(body: bytes, content_type: str, config: Config, asker: Asker) -> tuple[int, Any]:
    """(status, JSON) for a POST to /api/ask."""
    if content_type.split(";")[0].strip() != "application/json":
        return 415, {"error": "send JSON"}  # a form post from another page cannot be JSON
    try:
        question = str(json.loads(body[:MAX_BODY]).get("question", "")).strip()
    except (ValueError, AttributeError):
        return 400, {"error": "unreadable question"}
    if not question or len(question) > MAX_QUESTION:
        return 400, {"error": f"ask in 1 to {MAX_QUESTION} characters"}
    if not _busy.acquire(blocking=False):
        return 429, {"error": "still answering the last question"}
    try:
        answer, queries = asker(question, config)
    except FileNotFoundError:
        return 502, {"error": "Claude Code (claude) is not installed"}
    except subprocess.TimeoutExpired:
        return 502, {"error": "no answer in time"}
    except (OSError, LookupError) as exc:  # claude ran but gave nothing usable
        return 502, {"error": str(exc) or "no answer"}
    finally:
        _busy.release()
    return 200, {"answer": answer, "queries": queries}
