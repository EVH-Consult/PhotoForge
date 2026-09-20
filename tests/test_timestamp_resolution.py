# tests/test_timestamp_resolution.py

from __future__ import annotations

from datetime import datetime

from photoforge.model import TimestampCandidate
from photoforge.timestamp_resolution import resolve_timestamp_candidates


def test_exif_candidate_wins_over_filesystem_candidate() -> None:
    result = resolve_timestamp_candidates(
        (
            TimestampCandidate(
                source_kind="filesystem",
                source_detail="mtime",
                naive_timestamp=datetime(2024, 1, 2, 3, 4, 5),
                precision="datetime",
            ),
            TimestampCandidate(
                source_kind="exif",
                source_detail="exif_datetimeoriginal",
                naive_timestamp=datetime(2020, 6, 7, 8, 9, 10),
                precision="datetime",
            ),
        )
    )

    assert result.primary_candidate.source_kind == "exif"
    assert tuple(candidate.source_kind for candidate in result.valid_candidates) == (
        "exif",
        "filesystem",
    )


def test_date_only_candidate_uses_midnight_and_precedence() -> None:
    result = resolve_timestamp_candidates(
        (
            TimestampCandidate(
                source_kind="filename",
                source_detail="filename_date_only",
                naive_timestamp=datetime(2024, 1, 2, 0, 0, 0),
                precision="date",
            ),
            TimestampCandidate(
                source_kind="filesystem",
                source_detail="mtime",
                naive_timestamp=datetime(2024, 1, 2, 3, 4, 5),
                precision="datetime",
            ),
        )
    )

    assert result.primary_candidate.source_kind == "filename"
    assert tuple(candidate.source_kind for candidate in result.valid_candidates) == (
        "filename",
        "filesystem",
    )


def test_original_input_order_is_preserved_within_same_source_kind() -> None:
    result = resolve_timestamp_candidates(
        (
            TimestampCandidate(
                source_kind="exif",
                source_detail="exif_datetimeoriginal",
                naive_timestamp=datetime(2020, 1, 1, 10, 0, 0),
                precision="datetime",
            ),
            TimestampCandidate(
                source_kind="exif",
                source_detail="exif_datetimedigitized",
                naive_timestamp=datetime(2020, 1, 1, 11, 0, 0),
                precision="datetime",
            ),
        )
    )

    assert tuple(candidate.source_detail for candidate in result.valid_candidates) == (
        "exif_datetimeoriginal",
        "exif_datetimedigitized",
    )
    assert result.primary_candidate.source_detail == "exif_datetimeoriginal"
