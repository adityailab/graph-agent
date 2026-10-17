from __future__ import annotations

from pathlib import Path

import pytest

from handoff.demo.scratch import MARKER, NotAScratchFolder, prepare_scratch


def test_a_new_folder_is_created_and_marked(tmp_path: Path) -> None:
    folder = tmp_path / "demo"
    prepare_scratch(folder)
    assert (folder / MARKER).exists()


def test_a_folder_the_demo_made_is_reset(tmp_path: Path) -> None:
    folder = tmp_path / "demo"
    prepare_scratch(folder)
    (folder / "Checkout.tsx").write_text("old run")
    prepare_scratch(folder)
    assert not (folder / "Checkout.tsx").exists()
    assert (folder / MARKER).exists()


def test_any_other_folder_with_files_is_never_touched(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text("my real project")
    with pytest.raises(NotAScratchFolder):
        prepare_scratch(tmp_path)
    assert (tmp_path / "main.py").read_text() == "my real project"
    assert (tmp_path / ".git").is_dir()


def test_an_empty_folder_is_used(tmp_path: Path) -> None:
    prepare_scratch(tmp_path)
    assert (tmp_path / MARKER).exists()
