"""The dashboard's ask box: one question in, Claude's answer from the graphs and its Cypher out."""

from __future__ import annotations

import json
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from handoff.config import Config

Asker = Callable[
    [str, Config, list[tuple[str, str]], Callable[[str, str], None] | None], tuple[str, list[str]]
]
MAX_BODY = 32768
MAX_QUESTION = 500
MAX_CONTEXT = 600  # characters of "what the person is looking at"
MAX_TURNS = 6  # earlier turns the model is shown
MAX_ANSWER = 1500  # characters of each earlier answer
_busy = threading.Lock()  # one question at a time: each one spends the person's Claude plan


def _history(raw: object) -> list[tuple[str, str]] | None:
    """The most recent turns as (question, answer) pairs; None when the shape is wrong."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    turns: list[tuple[str, str]] = []
    for turn in raw[-MAX_TURNS:]:
        if not isinstance(turn, dict) or not all(isinstance(turn.get(k), str) for k in "qa"):
            return None
        turns.append((turn["q"][:MAX_QUESTION], turn["a"][:MAX_ANSWER]))
    return turns


@dataclass(frozen=True)
class AskRequest:
    question: str
    history: list[tuple[str, str]]
    stream: bool  # send the steps as they happen instead of one answer at the end
    context: str = ""  # what the person is looking at, so "this" can be answered


def parse_ask(body: bytes, content_type: str) -> AskRequest | tuple[int, Any]:
    """The request, or (status, JSON error) when it cannot be answered."""
    if content_type.split(";")[0].strip() != "application/json":
        return 415, {"error": "send JSON"}  # a form post from another page cannot be JSON
    try:
        sent = json.loads(body[:MAX_BODY])
        question = str(sent.get("question", "")).strip()
        history = _history(sent.get("history"))
        stream = sent.get("stream") is True
        raw = sent.get("context", "")
    except (ValueError, AttributeError):
        return 400, {"error": "unreadable question"}
    if history is None or not isinstance(raw, str):
        return 400, {"error": "unreadable history or context"}
    if not question or len(question) > MAX_QUESTION:
        return 400, {"error": f"ask in 1 to {MAX_QUESTION} characters"}
    return AskRequest(question, history, stream, " ".join(raw.split())[:MAX_CONTEXT])


def is_busy() -> bool:
    """True while a question is being answered."""
    return _busy.locked()


def run_ask(
    request: AskRequest,
    config: Config,
    asker: Asker,
    progress: Callable[[str, str], None] | None = None,
) -> tuple[int, Any]:
    """Ask, calling `progress(kind, text)` on the way (kind is step, text or thought);
    (status, JSON) at the end."""
    if not _busy.acquire(blocking=False):
        return 429, {"error": "still answering the last question"}
    try:
        asked = request.question
        if request.context:  # the model is told where the person is looking, not asked to guess
            asked += f"\n\n(The person is looking at: {request.context})"
        answer, queries = asker(asked, config, request.history, progress)
    except FileNotFoundError:
        return 502, {"error": "Claude Code (claude) is not installed"}
    except subprocess.TimeoutExpired:
        return 502, {"error": "no answer in time"}
    except (OSError, LookupError) as exc:  # claude ran but gave nothing usable
        return 502, {"error": str(exc) or "no answer"}
    finally:
        _busy.release()
    return 200, {"answer": answer, "queries": queries}
