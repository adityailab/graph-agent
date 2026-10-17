"""Turning history into text a session can read."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable, Sequence

from handoff.graph.conventions import Convention
from handoff.graph.records import InsightView, MessageView, RequestView, WhyRow
from handoff.graph.timeline import TimelineEntry

Paint = Callable[[str, str], str]  # (kind of text, text) -> text, e.g. with colour codes


def _unpainted(kind: str, text: str) -> str:
    return text


def select_requests(requests: Sequence[RequestView], limit: int) -> list[RequestView]:
    """Choose at most `limit` requests to show, in their original order.

    Requests with an open need come first, since they are the work another role is
    waiting on; the newest of the rest fill the remaining places.
    """
    if len(requests) <= limit:
        return list(requests)

    def priority(i: int) -> tuple[bool, int]:
        has_open_need = any(n.status == "open" for n in requests[i].needs)
        return (has_open_need, i)

    chosen = sorted(range(len(requests)), key=priority, reverse=True)[: max(limit, 0)]
    return [requests[i] for i in sorted(chosen)]


def shorten(text: str, limit: int = 300) -> str:
    """Cut text to `limit` characters, marking the cut."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _render_request(r: RequestView, paint: Paint) -> list[str]:
    lines = ["", f'Request {r.seq} (person): "{r.text}"']
    for d in r.decisions:
        label = "Decided (replaced later):" if d.superseded else "Decided:"
        lines.append(f"  {paint('decided', label)} {d.text}")
        lines.append(f"  {paint('why', 'Why:')} {d.reason}")
    if r.files:
        lines.append(f"  {paint('changed', 'Changed:')} {', '.join(r.files)}")
    for n in r.needs:
        label = paint("need", f"Needs from {n.for_role}:")
        lines.append(f"  {label} {n.text} ({paint(n.status, n.status)}, id {n.id})")
    return lines


def render_handoff(requests: Sequence[RequestView], paint: Paint = _unpainted) -> str:
    """Render requests grouped by role, with what each decided, changed and needs.
    `paint` marks the parts (role, decided, why, changed, need, a need's status) for colour; the
    default leaves the text plain, which is what sessions read."""
    if not requests:
        return "No requests recorded in this period."
    by_role: dict[str, list[RequestView]] = defaultdict(list)
    for request in requests:
        by_role[request.role].append(request)

    blocks: list[str] = []
    for role, items in by_role.items():
        files = {f for r in items for f in r.files}
        lines = [
            f"{paint('role', f'{role} session')}: {_plural(len(items), 'request')}, "
            f"{_plural(len(files), 'file')} changed"
        ]
        for r in items:
            lines.extend(_render_request(r, paint))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_why(path: str, rows: Sequence[WhyRow]) -> str:
    """Render the requests and decisions behind edits to one file, newest first."""
    lines = [f"Edits to {path}, newest first:"]
    for row in rows:
        lines.append("")
        lines.append(f'{row.role} session, request: "{shorten(row.request_text)}"')
        for d in row.decisions:
            lines.append(f"  Decided: {d.text}")
            lines.append(f"  Why: {d.reason}")
        first_line = row.edit_summary.splitlines()[0] if row.edit_summary else ""
        lines.append(f"  Change: {first_line}")
    return "\n".join(lines)


def _render_message(m: MessageView) -> str:
    when = time.strftime("%H:%M", time.localtime(m.at / 1000))
    m = MessageView(m.id, m.kind, m.from_role, shorten(m.text, 500), m.reply_to, m.at)
    if m.kind == "question":
        return (
            f'Question {m.id} from the {m.from_role} session ({when}): "{m.text}" '
            f"A reply goes through send_message with reply_to set to {m.id}."
        )
    if m.kind == "standin_answer":
        return (
            f"Stand-in answer {m.id} to question {m.reply_to} ({when}), written by a model "
            f'from this role\'s recorded history: "{m.text}" A correction goes through '
            f"send_message with reply_to set to {m.reply_to}."
        )
    reply = f", replying to {m.reply_to}" if m.reply_to else ""
    return f'Message {m.id} from the {m.from_role} session ({when}{reply}): "{m.text}"'


MAX_MESSAGES = 20


def render_messages(messages: Sequence[MessageView]) -> str:
    """Render delivered messages as statements of fact, one per line, capped."""
    shown = [_render_message(m) for m in messages[:MAX_MESSAGES]]
    hidden = len(messages) - len(shown)
    if hidden > 0:
        shown.append(f"{hidden} more messages arrived; they are not shown here.")
    return "\n".join(shown)


def render_insights(insights: Sequence[InsightView]) -> str:
    """The 'What matters now' section; empty when there is nothing to say."""
    if not insights:
        return ""
    return "What matters now:\n" + "\n".join(f"- {i.text}" for i in insights)


def _when(at: int) -> str:
    return time.strftime("%d %b %H:%M", time.localtime(at / 1000))


def render_timeline(topic: str, entries: Sequence[TimelineEntry]) -> str:
    """How decisions about a topic changed, oldest first, with what replaced what."""
    lines = [f"Decisions about {topic}, oldest first:"]
    for e in entries:
        note = f" [replaced by {e.replaced_by}]" if e.replaced_by else " [in force]"
        lines.append(f"- {_when(e.at)} {e.role} (decision {e.decision_id}){note}: {e.text}")
        lines.append(f"  Why: {e.reason}")
    return "\n".join(lines)


def render_conventions(conventions: Sequence[Convention]) -> str:
    """The standing rules, each with its reason and who it is for."""
    lines = []
    for c in conventions:
        who = "everyone" if c.scope == "all" else f"the {c.scope} role"
        lines.append(f"- {c.text} (for {who}, id {c.id}). Why: {c.reason}")
    return "\n".join(lines)


def render_earlier_decisions(entries: Sequence[TimelineEntry]) -> str:
    """A note listing decisions on the same topic that still stand."""
    lines = ["Earlier decisions on this topic still stand:"]
    lines += [f"- {e.decision_id} ({e.role}): {shorten(e.text, 160)}" for e in entries]
    lines.append(
        "If this one replaces an earlier one, call supersede_decision(decision_id, replaces)."
    )
    return "\n".join(lines)
