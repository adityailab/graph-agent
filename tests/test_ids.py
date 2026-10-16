from __future__ import annotations

from handoff.ids import new_id, now_ms


def test_new_ids_are_unique_hex() -> None:
    ids = {new_id() for _ in range(1000)}
    assert len(ids) == 1000
    assert all(len(i) == 32 and int(i, 16) >= 0 for i in ids)


def test_now_ms_is_epoch_milliseconds() -> None:
    assert 1_700_000_000_000 < now_ms() < 4_000_000_000_000
