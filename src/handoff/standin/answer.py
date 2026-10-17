"""Asking the model and checking what comes back."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from handoff.models.base import ModelClient, ModelUnavailable
from handoff.standin.context import StandinContext, context_ids
from handoff.standin.prompt import build_prompt


class StandinUnavailable(ModelUnavailable):
    """The model replied, but not with a usable answer."""


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


_MIN_PREFIX = 8
_KINDS = ("request", "decision", "need", "message")


def _resolve_citation(cited: str, allowed: set[str]) -> str | None:
    """The history id a citation means. Models often echo the line's "[decision <id>]"
    label or shorten the id; a prefix counts only if it is long and matches one id."""
    token = cited.strip().strip("[]").strip()
    words = token.split()
    if len(words) == 2 and words[0].lower() in _KINDS:
        token = words[1]
    if token in allowed:
        return token
    if len(token) < _MIN_PREFIX:
        return None
    matches = [i for i in allowed if i.startswith(token)]
    return matches[0] if len(matches) == 1 else None


def parse_answer(raw: str, *, allowed: set[str]) -> StandinAnswer | None:
    """Read the model's JSON, dropping citations not in the history. None if unusable."""
    data = _answer_object(raw)
    if data is None:
        return None
    text = str(data["answer"])
    cited = data.get("cited_ids")
    listed = cited if isinstance(cited, list) else []
    resolved = (_resolve_citation(i, allowed) for i in listed if isinstance(i, str))
    ids = tuple(dict.fromkeys(i for i in resolved if i))
    return StandinAnswer(text.strip(), ids, found=bool(data.get("found")))


def answer(client: ModelClient, ctx: StandinContext, question: str) -> StandinAnswer:
    """Ask the model for an answer grounded in `ctx`. Raises StandinUnavailable."""
    system, user = build_prompt(ctx, question)
    result = parse_answer(client.complete(system, user), allowed=context_ids(ctx))
    if result is None:
        raise StandinUnavailable("the model's reply was not a usable answer")
    return result
