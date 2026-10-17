"""Typed results returned by the read queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SessionInfo:
    id: str
    role: str
    cwd: str
    started_at: int
    last_seen_at: int


@dataclass(frozen=True)
class DecisionView:
    id: str
    text: str
    reason: str
    superseded: bool = False  # a later decision replaced this one
    at: int = field(default=0, compare=False)  # when it was decided, ms since the epoch


@dataclass(frozen=True)
class NeedView:
    id: str
    text: str
    for_role: str
    status: str


@dataclass(frozen=True)
class RequestView:
    id: str
    role: str
    seq: int
    text: str
    at: int
    files: tuple[str, ...]
    decisions: tuple[DecisionView, ...]
    needs: tuple[NeedView, ...]


@dataclass(frozen=True)
class WhyRow:
    role: str
    request_text: str
    decisions: tuple[DecisionView, ...]
    edit_summary: str
    at: int


def decision_views(raw: list[list[Any]]) -> tuple[DecisionView, ...]:
    """Convert collected [id, text, reason, superseded, at] lists, oldest decision first.

    An OPTIONAL MATCH with no match collects one list of nulls; it is dropped.
    """
    return tuple(
        sorted(
            (
                DecisionView(
                    id=str(i), text=str(t), reason=str(why), superseded=bool(gone), at=int(at or 0)
                )
                for i, t, why, gone, at in raw
                if i is not None
            ),
            key=lambda d: (d.at, d.id),  # ids are random, so only the time gives an order
        )
    )


@dataclass(frozen=True)
class MessageView:
    id: str
    kind: str  # "message", "question" or "standin_answer"
    from_role: str
    text: str
    reply_to: str | None
    at: int


@dataclass(frozen=True)
class DecisionHit:
    id: str
    role: str
    request_text: str
    text: str
    reason: str
    files: tuple[str, ...]
    related_roles: tuple[str, ...]  # other roles that changed the same files


@dataclass(frozen=True)
class OtherEdit:
    role: str
    request_text: str
    at: int


@dataclass(frozen=True)
class SharedFile:
    path: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class PathStep:
    label: str  # Request, Edit, File, Decision, Topic, Need, Message
    text: str  # what the node says: request text, file path, decision text, ...
    via: str  # relationship that led here ('' for the first step)


@dataclass(frozen=True)
class ItemRef:
    id: str
    kind: str  # "request" or "decision"
    role: str
    text: str


@dataclass(frozen=True)
class EntityRef:
    name: str
    type: str


@dataclass(frozen=True)
class InsightView:
    kind: str  # "collision", "load_bearing", "bridge" or "theme"
    score: float
    text: str
    about: tuple[str, ...]  # names of the nodes it is about
