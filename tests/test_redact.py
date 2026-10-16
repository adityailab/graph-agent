from __future__ import annotations

import pytest

from handoff.redact import REDACTED, redact


@pytest.mark.parametrize(
    "secret",
    [
        "sk-ant-api03-abcdefghijklmnopqrstuvwxyz012345",
        "sk-proj-abcdefghijklmnopqrstuvwxyz012345",
        "AKIAABCDEFGHIJKLMNOP",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        "github_pat_11ABCDEFG0abcdefghijklmnopqrstuvwxyz",
        "xoxb-1234567890-abcdefghij",
    ],
)
def test_known_key_formats_are_redacted(secret: str) -> None:
    text = f"use {secret} for the call"
    assert redact(text) == f"use {REDACTED} for the call"


def test_bearer_token_is_redacted_but_the_word_bearer_stays() -> None:
    assert redact("Authorization: Bearer abcdef0123456789abcdef") == (
        f"Authorization: Bearer {REDACTED}"
    )


def test_private_key_block_is_redacted() -> None:
    pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nabc\n-----END RSA PRIVATE KEY-----"
    assert redact(f"key:\n{pem}\nend") == f"key:\n{REDACTED}\nend"


def test_quoted_secret_assignment_keeps_its_name() -> None:
    assert redact('db_password = "hunter2hunter2"') == f'db_password = "{REDACTED}"'


def test_env_file_secret_line_keeps_its_name() -> None:
    assert redact("STRIPE_API_KEY=abcd1234efgh\nDEBUG=true") == (
        f"STRIPE_API_KEY={REDACTED}\nDEBUG=true"
    )


@pytest.mark.parametrize(
    "text",
    [
        "Show the user's full name and avatar on the profile card",
        "token = get_token(user)",
        "def refresh_token(session): return session.token",
        "The password field should be masked in the form",
    ],
)
def test_ordinary_prose_and_code_are_unchanged(text: str) -> None:
    assert redact(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+DB_PASSWORD=hunter2hunter2", f"+DB_PASSWORD={REDACTED}"),
        ("export GITHUB_TOKEN=abcdef123456", f"export GITHUB_TOKEN={REDACTED}"),
        ('{"api_key": "abcdef123456"}', f'{{"api_key": "{REDACTED}"}}'),
    ],
)
def test_secrets_in_diffs_exports_and_json_are_redacted(text: str, expected: str) -> None:
    assert redact(text) == expected


def test_private_key_without_its_end_line_is_redacted() -> None:
    assert redact("-----BEGIN PRIVATE KEY-----\nMIIEow\nabc") == REDACTED
