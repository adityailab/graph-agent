"""Asking the model and checking what comes back."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from handoff.standin.context import StandinContext, context_ids
from handoff.standin.prompt import build_prompt

_UNUSABLE = "The stand-in could not produce a usable answer from the recorded history."


class StandinUnavailable(Exception):  # noqa: N818 - reads as a state, matching how it is used
    """Raised when the model cannot be reached or fails."""


class ModelClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


@dataclass(frozen=True)
class StandinAnswer:
    text: str
    cited_ids: tuple[str, ...]
    found: bool


def _json_object(raw: str) -> object:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match is None:
        raise ValueError("no JSON object")
    return json.loads(match.group(0))


def parse_answer(raw: str, *, allowed: set[str]) -> StandinAnswer:
    """Read the model's JSON; drop citations not in the history; never raise."""
    try:
        data = _json_object(raw)
    except (ValueError, json.JSONDecodeError):
        return StandinAnswer(_UNUSABLE, (), found=False)
    if not isinstance(data, dict) or not isinstance(data.get("answer"), str):
        return StandinAnswer(_UNUSABLE, (), found=False)
    cited = data.get("cited_ids")
    ids = (
        tuple(i for i in cited if isinstance(i, str) and i in allowed)
        if isinstance(cited, list)
        else ()
    )
    return StandinAnswer(data["answer"].strip(), ids, found=bool(data.get("found")))


def answer(client: ModelClient, ctx: StandinContext, question: str) -> StandinAnswer:
    """Ask the model for an answer grounded in `ctx`. Raises StandinUnavailable."""
    system, user = build_prompt(ctx, question)
    return parse_answer(client.complete(system, user), allowed=context_ids(ctx))
