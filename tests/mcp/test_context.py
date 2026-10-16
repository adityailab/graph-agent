from __future__ import annotations

from pathlib import Path

from handoff.mcp.context import context_from_env


def test_context_resolves_a_symlinked_project_folder(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    ctx = context_from_env(
        {"CLAUDE_PROJECT_DIR": str(link)}, cwd="/elsewhere", connect=lambda: None
    )
    assert ctx.cwd == str(real.resolve())
    assert ctx.role == "real"


def test_context_role_comes_from_the_environment_lower_cased() -> None:
    ctx = context_from_env({"HANDOFF_ROLE": " Backend "}, cwd="/w", connect=lambda: None)
    assert ctx.role == "backend"


def test_context_takes_the_session_id_claude_code_provides() -> None:
    ctx = context_from_env({"CLAUDE_CODE_SESSION_ID": "abc"}, cwd="/w", connect=lambda: None)
    assert ctx.session_id == "abc"
