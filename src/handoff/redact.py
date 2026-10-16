"""Removing secrets from prompt and diff text before it is stored."""

from __future__ import annotations

import re

REDACTED = "[redacted]"

# Whole matches that are always secrets.
_WHOLE = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
]

# Patterns where a name stays visible and only the value (group "value") is secret.
_VALUE = [
    re.compile(r"(?i)\bbearer\s+(?P<value>[A-Za-z0-9._~+/=-]{16,})"),
    re.compile(
        r"(?i)\b\w*(?:password|passwd|secret|token|api[_-]?key)\w*\s*[:=]\s*"
        r"(?P<quote>[\"'])(?P<value>[^\"'\n]{6,})(?P=quote)"
    ),
    re.compile(r"(?m)^[A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|API_KEY)[A-Z0-9_]*=(?P<value>\S+)$"),
]


def _hide_value(match: re.Match[str]) -> str:
    start, end = match.span("value")
    whole_start = match.start()
    text = match.group(0)
    return text[: start - whole_start] + REDACTED + text[end - whole_start :]


def redact(text: str) -> str:
    """Return `text` with API keys, tokens, private keys and secret assignments hidden."""
    for pattern in _WHOLE:
        text = pattern.sub(REDACTED, text)
    for pattern in _VALUE:
        text = pattern.sub(_hide_value, text)
    return text
