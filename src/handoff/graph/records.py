"""Typed results returned by the read queries."""

from __future__ import annotations

from dataclasses import dataclass


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
    decision_text: str | None
    decision_reason: str | None
    edit_summary: str
    at: int
