from __future__ import annotations

from handoff.prereqs import check_prerequisites
from tests.cli.fakes import fake_runner


def _all_found(name: str) -> str:
    return f"/usr/bin/{name}"


def test_everything_present_is_no_problem() -> None:
    assert check_prerequisites(fake_runner([]), which=_all_found, need_docker=True) == []


def test_docker_not_running_is_one_problem_with_a_fix() -> None:
    problems = check_prerequisites(fake_runner([], code=1), which=_all_found, need_docker=True)
    assert [p.name for p in problems] == ["docker"]
    assert "colima start" in problems[0].fix


def test_docker_is_not_needed_when_the_database_already_answers() -> None:
    assert check_prerequisites(fake_runner([], code=1), which=_all_found, need_docker=False) == []


def test_missing_claude_is_required_and_missing_npx_is_optional() -> None:
    problems = check_prerequisites(
        fake_runner([]),
        which=lambda n: None if n in ("claude", "npx") else _all_found(n),
        need_docker=False,
    )
    assert [(p.name, p.optional) for p in problems] == [("claude", False), ("npx", True)]
