"""The words the stand-in model sees."""

from __future__ import annotations

from handoff.standin.context import StandinContext

SYSTEM = (
    "You answer one question on behalf of the {role} session in a software project, using "
    "only that session's recorded history, which the user message lists. Every line of the "
    "history starts with an id in brackets. Do not use outside knowledge or guess. Reply "
    "with a single JSON object and nothing else, in this shape: "
    '{{"answer": "<two sentences at most>", "cited_ids": ["<ids of the lines you relied '
    'on>"], "found": <true or false>}}. When the history does not answer the question, set '
    '"found" to false, leave "cited_ids" empty, and say in "answer" that the history does '
    "not cover it."
)


def _history_lines(ctx: StandinContext) -> list[str]:
    lines: list[str] = []
    for r in ctx.requests:
        lines.append(f'[request {r.id}] The person asked the {r.role} session: "{r.text}"')
        lines.extend(f"[decision {d.id}] Decided: {d.text}. Why: {d.reason}" for d in r.decisions)
        lines.extend(
            f"[need {n.id}] Needs from {n.for_role}: {n.text} ({n.status})" for n in r.needs
        )
        if r.files:
            lines.append(f"  (changed {', '.join(r.files)})")
    lines.extend(
        f'[message {m.id}] {m.from_role} session wrote ({m.kind}): "{m.text}"' for m in ctx.messages
    )
    return lines


def build_prompt(ctx: StandinContext, question: str) -> tuple[str, str]:
    """Return the system prompt and the user message for one question."""
    history = "\n".join(_history_lines(ctx)) or "(no recorded history)"
    user = f"History of the {ctx.role} session:\n{history}\n\nQuestion: {question}"
    return SYSTEM.format(role=ctx.role), user
