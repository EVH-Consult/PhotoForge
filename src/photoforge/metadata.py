# src/photoforge/metadata.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,  timezone

from .model import TimestampCandidate


@dataclass(frozen=True)
class NormalizedMetadata:
    timestamp: datetime
    timestamp_source: str


def normalize_metadata(primary_candidate: TimestampCandidate) -> NormalizedMetadata:
    if primary_candidate.precision != "datetime":
        raise ValueError('primary_candidate.precision must be "datetime"')

    naive = primary_candidate.naive_timestamp
    source = primary_candidate.source_detail
    offset = primary_candidate.timezone_offset

    if offset is None:
        return NormalizedMetadata(
            timestamp=naive,
            timestamp_source=source,
        )

    try:
        aware = naive.replace(tzinfo=timezone(offset))
    except ValueError as exc:
        raise ValueError("timezone_offset is invalid") from exc

    return NormalizedMetadata(
        timestamp=aware.astimezone(timezone.utc).replace(tzinfo=None),
        timestamp_source=source,
    )
