# src/photoforge/metadata_extractors/filename.py

from __future__ import annotations

import re
from datetime import datetime
from typing import Final

from photoforge.model import TimestampCandidate


# Patterns (ordered: full datetime first, then date-only)
_PATTERNS: Final[list[tuple[str, str]]] = [
    ("filename_yyyymmdd_hhmmss", r"(?<!\d)(\d{8})_(\d{6})(?!\d)"),
    ("filename_yyyy-mm-dd_hh-mm-ss", r"(?<!\d)(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})(?!\d)"),
    ("filename_yyyy-mm-dd_hh-mm-ss_space", r"(?<!\d)(\d{4}-\d{2}-\d{2}) (\d{2}-\d{2}-\d{2})(?!\d)"),
    ("filename_yyyymmdd", r"(?<!\d)(\d{8})(?!\d)"),
    ("filename_yyyy-mm-dd", r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)"),
]


def extract_filename_timestamp(filename: str) -> tuple[TimestampCandidate, ...]:
    matches: list[tuple[int, int, str, re.Match[str]]] = []

    for priority, (source_detail, pattern) in enumerate(_PATTERNS):
        for match in re.finditer(pattern, filename):
            start = match.start()
            matches.append((start, priority, source_detail, match))

    if not matches:
        return ()

    # Sort: left-to-right first, then pattern priority (full before date)
    matches.sort(key=lambda x: (x[0], x[1]))

    for _, _, source_detail, match in matches:
        try:
            if match.lastindex == 2:
                dt = _parse_full_datetime(match, source_detail)
                return (
                    TimestampCandidate(
                        source_kind="filename",
                        source_detail=source_detail,
                        naive_timestamp=dt,
                        precision="datetime",
                        timezone_offset=None,
                    ),
                )
            else:
                dt = _parse_date_only(match, source_detail)
                return (
                    TimestampCandidate(
                        source_kind="filename",
                        source_detail=source_detail,
                        naive_timestamp=dt,
                        precision="date",
                        timezone_offset=None,
                    ),
                )
        except ValueError:
            continue

    return ()


def _parse_full_datetime(match: re.Match[str], source_detail: str) -> datetime:
    date_part = match.group(1)
    time_part = match.group(2)

    if "yyyymmdd" in source_detail:
        year = int(date_part[0:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[0:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6])
    else:
        y, m, d = date_part.split("-")
        h, mi, s = time_part.split("-")
        year, month, day = int(y), int(m), int(d)
        hour, minute, second = int(h), int(mi), int(s)

    return datetime(year, month, day, hour, minute, second)


def _parse_date_only(match: re.Match[str], source_detail: str) -> datetime:
    date_part = match.group(1)

    if "yyyymmdd" in source_detail:
        year = int(date_part[0:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
    else:
        y, m, d = date_part.split("-")
        year, month, day = int(y), int(m), int(d)

    return datetime(year, month, day, 0, 0, 0)
