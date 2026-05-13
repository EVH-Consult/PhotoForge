# tests/test_metadata.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from photoforge.metadata import NormalizedMetadata, normalize_metadata
from photoforge.model import TimestampCandidate


def test_normalize_metadata_without_timezone_uses_naive_timestamp() -> None:
    candidate = TimestampCandidate(
        source_kind="filesystem",
        source_detail="filesystem_mtime",
        naive_timestamp=datetime(2024, 1, 2, 3, 4, 5),
        precision="datetime",
        timezone_offset=None,
    )

    result = normalize_metadata(candidate)

    assert result == NormalizedMetadata(
        timestamp=datetime(2024, 1, 2, 3, 4, 5),
        timestamp_source="filesystem_mtime",
    )


def test_normalize_metadata_with_timezone_uses_utc_timestamp() -> None:
    candidate = TimestampCandidate(
        source_kind="exif",
        source_detail="exif_datetimeoriginal",
        naive_timestamp=datetime(2024, 1, 2, 3, 4, 5),
        precision="datetime",
        timezone_offset=timedelta(hours=2, minutes=30),
    )

    result = normalize_metadata(candidate)

    assert result == NormalizedMetadata(
        timestamp=datetime(2024, 1, 2, 0, 34, 5, tzinfo=timezone.utc),
        timestamp_source="exif_datetimeoriginal",
    )


def test_normalize_metadata_accepts_date_precision() -> None:
    candidate = TimestampCandidate(
        source_kind="filename",
        source_detail="filename_yyyymmdd",
        naive_timestamp=datetime(2024, 1, 2, 0, 0, 0),
        precision="date",
        timezone_offset=None,
    )

    result = normalize_metadata(candidate)

    assert result == NormalizedMetadata(
        timestamp=datetime(2024, 1, 2, 0, 0, 0),
        timestamp_source="filename_yyyymmdd",
    )


def test_timestamp_candidate_rejects_aware_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="naive_timestamp must be naive"):
        TimestampCandidate(
            source_kind="exif",
            source_detail="exif_datetimeoriginal",
            naive_timestamp=datetime(
                2024,
                1,
                2,
                3,
                4,
                5,
                tzinfo=timezone.utc,
            ),
            precision="datetime",
            timezone_offset=None,
        )


def test_normalize_metadata_propagates_invalid_timezone_offset() -> None:
    candidate = TimestampCandidate(
        source_kind="exif",
        source_detail="exif_datetimeoriginal",
        naive_timestamp=datetime(2024, 1, 2, 3, 4, 5),
        precision="datetime",
        timezone_offset=timedelta(hours=30),
    )

    with pytest.raises(ValueError, match="offset must be a timedelta"):
        normalize_metadata(candidate)