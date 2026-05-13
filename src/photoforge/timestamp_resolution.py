# src/photoforge/timestamp_resolution.py

from __future__ import annotations

from datetime import timezone

from .model import TimestampCandidate, TimestampResolutionResult

_SOURCE_PRECEDENCE: dict[str, int] = {
    "exif": 0,
    "filename": 1,
    "folder": 2,
    "filesystem": 3,
}


def resolve_timestamp_candidates(
    candidates: tuple[TimestampCandidate, ...],
) -> TimestampResolutionResult:
    indexed_valid_candidates: list[tuple[int, int, TimestampCandidate]] = []

    for index, candidate in enumerate(candidates):
        if not is_valid_timestamp_candidate(candidate):
            continue

        precedence = _SOURCE_PRECEDENCE.get(candidate.source_kind)
        if precedence is None:
            raise ValueError(f"unsupported source_kind: {candidate.source_kind}")

        indexed_valid_candidates.append((precedence, index, candidate))

    if not indexed_valid_candidates:
        raise ValueError("no valid timestamp candidates available")

    sorted_valid_candidates = tuple(
        candidate
        for _, _, candidate in sorted(
            indexed_valid_candidates,
            key=lambda item: (item[0], item[1]),
        )
    )

    return TimestampResolutionResult(
        primary_candidate=sorted_valid_candidates[0],
        valid_candidates=sorted_valid_candidates,
    )


def is_valid_timestamp_candidate(candidate: TimestampCandidate) -> bool:
    if candidate.precision not in {"date", "datetime"}:
        return False

    if candidate.naive_timestamp.tzinfo is not None:
        return False

    if candidate.source_kind not in _SOURCE_PRECEDENCE:
        return False

    if candidate.timezone_offset is None:
        return True

    try:
        timezone(candidate.timezone_offset)
    except Exception:
        return False

    return True