"""Typed results returned by the read queries."""

from __future__ import annotations

from dataclasses import dataclass
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
    """Convert collected [id, text, reason] lists, sorted by id.

    An OPTIONAL MATCH with no match collects one list of nulls; it is dropped.
    """
    return tuple(
        sorted(
            (
                DecisionView(id=str(i), text=str(t), reason=str(why))
                for i, t, why in raw
                if i is not None
            ),
            key=lambda d: d.id,
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
