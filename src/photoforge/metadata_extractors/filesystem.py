# src/photoforge/metadata_extractors/filesystem.py

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from ..model import TimestampCandidate


def extract_filesystem_timestamp_candidates(
    path: Path,
    mtime_timestamp: float,
) -> tuple[TimestampCandidate, ...]:
    _ = mtime_timestamp

    stat_result = os.stat(path)
    candidates: list[TimestampCandidate] = []

    candidates.extend(_candidate_from_timestamp("filesystem_mtime", stat_result.st_mtime))

    birthtime_value = getattr(stat_result, "st_birthtime", None)
    if birthtime_value is not None:
        candidates.extend(_candidate_from_timestamp("filesystem_birthtime", birthtime_value))

    return tuple(candidates)


def _candidate_from_timestamp(
    source_detail: str,
    timestamp_value: float,
) -> tuple[TimestampCandidate, ...]:
    try:
        naive_timestamp = datetime.fromtimestamp(timestamp_value)
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