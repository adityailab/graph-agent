"""Turning history into text a session can read."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Sequence

from handoff.graph.records import MessageView, RequestView, WhyRow


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


def _render_request(r: RequestView) -> list[str]:
    lines = ["", f'Request {r.seq} (person): "{r.text}"']
    for d in r.decisions:
        lines.append(f"  Decided: {d.text}")
        lines.append(f"  Why: {d.reason}")
    if r.files:
        lines.append(f"  Changed: {', '.join(r.files)}")
    for n in r.needs:
        lines.append(f"  Needs from {n.for_role}: {n.text} ({n.status}, id {n.id})")
    return lines


def render_handoff(requests: Sequence[RequestView]) -> str:
    """Render requests grouped by role, with what each decided, changed and needs."""
    if not requests:
        return "No requests recorded in this period."
    by_role: dict[str, list[RequestView]] = defaultdict(list)
    for request in requests:
        by_role[request.role].append(request)

    blocks: list[str] = []
    for role, items in by_role.items():
        files = {f for r in items for f in r.files}
        lines = [
            f"{role} session: {_plural(len(items), 'request')}, "
            f"{_plural(len(files), 'file')} changed"
        ]
        for r in items:
            lines.extend(_render_request(r))
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
