"""The coordinator's rules. Each one finds a situation in the graph, and acts only by
sending a message from the 'coordinator' role; nothing is edited and no model is called."""

from __future__ import annotations

from dataclasses import dataclass

from falkordb import Graph

from handoff.format import render_insights
from handoff.graph.coordination import (
    action_taken,
    claim_and_send,
    recent_collisions,
    stale_needs,
)
from handoff.graph.history import handoff_requests
from handoff.graph.insights import current_insights
from handoff.graph.needs import count_open_needs
from handoff.graph.sessions import upsert_session
from handoff.ids import new_id

MINUTE_MS = 60_000
COORDINATOR = "coordinator"
PERSON = "person"


@dataclass(frozen=True)
class Thresholds:
    stale_minutes: int = 30
    collision_minutes: int = 60
    digest_minutes: int = 0  # 0 = no digest


@dataclass(frozen=True)
class Action:
    rule: str  # stale_need, collision or digest
    to_roles: tuple[str, ...]
    text: str
    kind: str = "nudge"  # a message kind of its own: not a fact about the role (digest: "digest")


def _deliver(graph: Graph, key: str, action: Action, *, at: int) -> bool:
    upsert_session(graph, session_id=COORDINATOR, role=COORDINATOR, cwd="", at=at)
    return claim_and_send(
        graph,
        key=key,
        rule=action.rule,
        kind=action.kind,
        text=action.text,
        at=at,
        sender=COORDINATOR,
        deliveries=[(new_id(), role) for role in action.to_roles],
    )


def _stale(graph: Graph, now: int, t: Thresholds) -> list[tuple[str, Action]]:
    found = []
    for need in stale_needs(graph, cutoff=now - t.stale_minutes * MINUTE_MS):
        minutes = (now - need.at) // MINUTE_MS
        text = (
            f"Reminder from the coordinator: need {need.id} from {need.raised_by} has been "
            f"open {minutes} min: {need.text} resolve_need closes it once it is met."
        )
        found.append((f"stale_need:{need.id}", Action("stale_need", (need.for_role,), text)))
    return found


def _collisions(graph: Graph, now: int, t: Thresholds) -> list[tuple[str, Action]]:
    found = []
    for c in recent_collisions(graph, since=now - t.collision_minutes * MINUTE_MS):
        text = (
            f"Heads-up from the coordinator: {c.first_role} and {c.second_role} have both "
            f"changed {c.path} recently. handoff shows what each did and why."
        )
        key = f"collision:{c.path}:{c.first_role}:{c.second_role}"
        found.append((key, Action("collision", (c.first_role, c.second_role), text)))
    return found


def _digest(graph: Graph, now: int, t: Thresholds) -> list[tuple[str, Action]]:
    if t.digest_minutes <= 0:
        return []
    window = t.digest_minutes * MINUTE_MS
    requests = handoff_requests(graph, role=None, since=now - window)
    if not requests:
        return []
    lines = []
    for role in sorted({r.role for r in requests}):
        mine = [r for r in requests if r.role == role]
        files = {f for r in mine for f in r.files}
        lines.append(f"- {role}: {len(mine)} requests, {len(files)} files changed")
    needs = sum(count_open_needs(graph, role) for role in {r.role for r in requests})
    plural = "" if needs == 1 else "s"
    parts = [
        f"Digest from the coordinator for the last {t.digest_minutes} minutes:",
        *lines,
        f"{needs} open need{plural}.",
    ]
    matters = render_insights(current_insights(graph, limit=3))
    text = "\n".join(parts + ([matters] if matters else []))
    return [(f"digest:{now // window}", Action("digest", (PERSON,), text, kind="digest"))]


def run_rules(
    graph: Graph, *, now: int, thresholds: Thresholds, dry_run: bool = False
) -> list[Action]:
    """Apply every rule once; return the actions taken (or, in a dry run, that would be)."""
    taken = []
    for rule in (_stale, _collisions, _digest):
        for key, action in rule(graph, now, thresholds):
            if dry_run:
                if not action_taken(graph, key=key):
                    taken.append(action)
            elif _deliver(graph, key, action, at=now):
                taken.append(action)
    return taken
