from __future__ import annotations

from pathlib import Path

from handoff.paths import relative_path


def test_paths_inside_the_project_become_relative() -> None:
    assert relative_path("/work/app/src/a.ts", "/work/app") == "src/a.ts"


def test_paths_outside_the_project_stay_absolute() -> None:
    assert relative_path("/etc/hosts", "/work/app") == "/etc/hosts"


def test_paths_through_a_symlinked_project_are_relative(tmp_path: Path) -> None:
    real = tmp_path / "real"
    (real / "src").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(real)
    assert relative_path(str(real / "src" / "a.ts"), str(link)) == "src/a.ts"
