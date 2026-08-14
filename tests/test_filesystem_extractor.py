from __future__ import annotations

from datetime import datetime
from pathlib import Path

from photoforge.metadata_extractors.filesystem import extract_filesystem_timestamp_candidates


def test_extracts_only_utc_normalized_mtime() -> None:
    result = extract_filesystem_timestamp_candidates(Path("dummy.jpg"), 1704164645.0)
    assert len(result) == 1
    assert result[0].source_detail == "filesystem_mtime"
    assert result[0].naive_timestamp == datetime(2024, 1, 2, 3, 4, 5)
    assert result[0].naive_timestamp.tzinfo is None


def test_invalid_timestamp_is_ignored() -> None:
    assert extract_filesystem_timestamp_candidates(Path("dummy.jpg"), float("nan")) == ()
