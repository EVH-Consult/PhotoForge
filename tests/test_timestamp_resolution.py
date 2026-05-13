# tests/test_timestamp_resolution.py

from __future__ import annotations

from datetime import datetime

from photoforge.model import TimestampCandidate
from photoforge.timestamp_resolution import resolve_timestamp_candidates

def test_date_only_candidate_is_valid_for_resolution() -> None:
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