"""Asking the model and checking what comes back."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from handoff.standin.context import StandinContext, context_ids
from handoff.standin.prompt import build_prompt


class StandinUnavailable(Exception):  # noqa: N818 - reads as a state, matching how it is used
    """Raised when the model cannot be reached or fails."""


class ModelClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


@dataclass(frozen=True)
class StandinAnswer:
    text: str
    cited_ids: tuple[str, ...]
    found: bool


def _answer_object(raw: str) -> dict[str, object] | None:
    """The first JSON object in `raw` that has a string "answer", wherever it sits."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", raw):
        try:
            data, _ = decoder.raw_decode(raw, match.start())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("answer"), str):
            return data
    return None


def parse_answer(raw: str, *, allowed: set[str]) -> StandinAnswer | None:
    """Read the model's JSON, dropping citations not in the history. None if unusable."""
    data = _answer_object(raw)
    if data is None:
        return None
    text = str(data["answer"])
    cited = data.get("cited_ids")
    ids = (
        tuple(i for i in cited if isinstance(i, str) and i in allowed)
        if isinstance(cited, list)
        else ()
    )
    return StandinAnswer(text.strip(), ids, found=bool(data.get("found")))


def answer(client: ModelClient, ctx: StandinContext, question: str) -> StandinAnswer:
    """Ask the model for an answer grounded in `ctx`. Raises StandinUnavailable."""
    system, user = build_prompt(ctx, question)
    result = parse_answer(client.complete(system, user), allowed=context_ids(ctx))
    if result is None:
        raise StandinUnavailable("the model's reply was not a usable answer")
    return result
