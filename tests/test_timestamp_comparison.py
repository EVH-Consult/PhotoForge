# tests/test_timestamp_comparison.py

from __future__ import annotations

from datetime import datetime, timedelta

from photoforge.model import TimestampCandidate
from photoforge.timestamp_diagnostics import (
    build_metadata_diagnostics,
    compare_timestamp_candidates,
)


def test_compare_utc_candidates_equal() -> None:
    left = TimestampCandidate(
        source_kind="exif",
        source_detail="source_a",
        naive_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        precision="datetime",
        timezone_offset=timedelta(hours=1),
    )

    right = TimestampCandidate(
        source_kind="exif",
        source_detail="source_b",
        naive_timestamp=datetime(2024, 1, 1, 9, 0, 0),
        precision="datetime",
        timezone_offset=timedelta(0),
    )

    comparison = compare_timestamp_candidates(left, right)

    assert comparison is not None
    assert comparison.representation == "utc"
    assert comparison.equal is True


def test_compare_naive_candidates_equal() -> None:
    left = TimestampCandidate(
        source_kind="filename",
        source_detail="source_a",
        naive_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        precision="datetime",
    )

    right = TimestampCandidate(
        source_kind="folder",
        source_detail="source_b",
        naive_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        precision="datetime",
    )

    comparison = compare_timestamp_candidates(left, right)

    assert comparison is not None
    assert comparison.representation == "naive"
    assert comparison.equal is True


def test_aware_and_naive_are_not_compared() -> None:
    aware = TimestampCandidate(
        source_kind="exif",
        source_detail="source_a",
        naive_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        precision="datetime",
        timezone_offset=timedelta(hours=1),
    )

    naive = TimestampCandidate(
        source_kind="filename",
        source_detail="source_b",
        naive_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        precision="datetime",
    )

    comparison = compare_timestamp_candidates(aware, naive)

    assert comparison is None


def test_build_metadata_diagnostics_detects_inconsistency() -> None:
    left = TimestampCandidate(
        source_kind="filename",
        source_detail="source_a",
        naive_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        precision="datetime",
    )

    right = TimestampCandidate(
        source_kind="folder",
        source_detail="source_b",
        naive_timestamp=datetime(2024, 1, 1, 11, 0, 0),
        precision="datetime",
    )

    diagnostics = build_metadata_diagnostics((right, left))

    assert len(diagnostics.comparisons) == 1
    assert len(diagnostics.inconsistent_pairs) == 1
    assert diagnostics.has_inconsistency is True


def test_build_metadata_diagnostics_ignores_same_source_pairs() -> None:
    first = TimestampCandidate(
        source_kind="filename",
        source_detail="source_a",
        naive_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        precision="datetime",
    )

    second = TimestampCandidate(
        source_kind="filename",
        source_detail="source_a",
        naive_timestamp=datetime(2024, 1, 1, 11, 0, 0),
        precision="datetime",
    )

    diagnostics = build_metadata_diagnostics((second, first))

    assert diagnostics.comparisons == ()
    assert diagnostics.inconsistent_pairs == ()
    assert diagnostics.has_inconsistency is False