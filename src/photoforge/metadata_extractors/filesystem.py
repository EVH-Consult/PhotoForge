# src/photoforge/metadata_extractors/filesystem.py

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..model import TimestampCandidate


def extract_filesystem_timestamp_candidates(
    path: Path,
    mtime_timestamp: float,
) -> tuple[TimestampCandidate, ...]:
    _ = path
    return _candidate_from_timestamp("filesystem_mtime", mtime_timestamp)


def _candidate_from_timestamp(
    source_detail: str,
    timestamp_value: float,
) -> tuple[TimestampCandidate, ...]:
    try:
        naive_timestamp = datetime.fromtimestamp(
            timestamp_value, tz=timezone.utc
        ).replace(tzinfo=None)
    except (OverflowError, OSError, ValueError):
        return ()

    return (
        TimestampCandidate(
            source_kind="filesystem",
            source_detail=source_detail,
            naive_timestamp=naive_timestamp,
            precision="datetime",
            timezone_offset=None,
        ),
    )
