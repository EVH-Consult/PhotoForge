from __future__ import annotations

from datetime import datetime, timedelta

from photoforge.model import TimestampCandidate
from photoforge.timestamp_diagnostics import compare_timestamp_candidates


def _candidate(value: datetime, source: str, offset: timedelta | None = None) -> TimestampCandidate:
    return TimestampCandidate("exif", source, value, "datetime", offset)


def test_compare_utc_candidates_equal() -> None:
    comparison = compare_timestamp_candidates(
        _candidate(datetime(2024, 1, 1, 10), "a", timedelta(hours=1)),
        _candidate(datetime(2024, 1, 1, 9), "b", timedelta()),
    )
    assert comparison is not None
    assert comparison.representation == "utc"
    assert comparison.equal is True


def test_compare_naive_candidates_equal() -> None:
    comparison = compare_timestamp_candidates(
        _candidate(datetime(2024, 1, 1, 10), "a"),
        _candidate(datetime(2024, 1, 1, 10), "b"),
    )
    assert comparison is not None
    assert comparison.representation == "naive"
    assert comparison.equal is True


def test_aware_and_naive_are_not_compared() -> None:
    comparison = compare_timestamp_candidates(
        _candidate(datetime(2024, 1, 1, 10), "a", timedelta(hours=1)),
        _candidate(datetime(2024, 1, 1, 10), "b"),
    )
    assert comparison is None
