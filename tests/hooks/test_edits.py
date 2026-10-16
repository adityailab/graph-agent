from __future__ import annotations

from pathlib import Path

from handoff.hooks.edits import MAX_SUMMARY_CHARS, edited_path, relative_path, summarise


def test_edit_summary_is_a_diff_without_file_headers() -> None:
    summary = summarise("Edit", {"old_string": "hi\nkeep", "new_string": "hello\nkeep"})
    assert "-hi" in summary
    assert "+hello" in summary
    assert "---" not in summary
    assert "+++" not in summary


def test_write_summary_counts_lines_and_shows_the_start() -> None:
    summary = summarise("Write", {"content": "one\ntwo\n"})
    assert summary.startswith("wrote 2 lines")
    assert "one" in summary


def test_notebook_summary_names_the_cell() -> None:
    summary = summarise("NotebookEdit", {"cell_id": "c1", "new_source": "x = 1"})
    assert summary.startswith("replace cell c1")
    assert "x = 1" in summary


def test_long_summaries_are_capped() -> None:
    content = "\n".join(f"line {i} " + "x" * 200 for i in range(500))
    summary = summarise("Write", {"content": content})
    assert len(summary.splitlines()) <= 41
    assert len(summary) <= MAX_SUMMARY_CHARS + 40


def test_paths_inside_the_project_become_relative() -> None:
    assert relative_path("/work/app/src/a.ts", "/work/app") == "src/a.ts"


def test_paths_outside_the_project_stay_absolute() -> None:
    assert relative_path("/etc/hosts", "/work/app") == "/etc/hosts"


def test_edited_path_reads_file_or_notebook_path() -> None:
    assert edited_path({"file_path": "/a.py"}) == "/a.py"
    assert edited_path({"notebook_path": "/n.ipynb"}) == "/n.ipynb"
    assert edited_path({}) is None


def test_paths_through_a_symlinked_project_are_relative(tmp_path: Path) -> None:
    real = tmp_path / "real"
    (real / "src").mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(real)
    assert relative_path(str(real / "src" / "a.ts"), str(link)) == "src/a.ts"
