from __future__ import annotations

from pathlib import Path

from handoff.leader import LeaderLock


def test_only_one_holder_at_a_time(tmp_path: Path) -> None:
    first, second = LeaderLock(tmp_path / "l.lock"), LeaderLock(tmp_path / "l.lock")
    assert first.acquire() is True
    assert second.acquire() is False
    first.release()
    assert second.acquire() is True
    second.release()


def test_releasing_without_holding_is_harmless(tmp_path: Path) -> None:
    LeaderLock(tmp_path / "l.lock").release()


def test_asking_again_while_holding_is_still_yes(tmp_path: Path) -> None:
    lock = LeaderLock(tmp_path / "l.lock")
    assert lock.acquire() is True
    assert lock.acquire() is True
    assert lock.held is True
    lock.release()
    assert lock.held is False
