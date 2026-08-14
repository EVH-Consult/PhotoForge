from __future__ import annotations

import os
from pathlib import Path

from .model import (
    ContextualGroup,
    ContextualGrouping,
    FileRecord,
    compute_group_id,
)

TIME_WINDOW_SECONDS = 300


def build_contextual_grouping(records: tuple[FileRecord, ...]) -> ContextualGrouping:
    """Build a deterministic contextual grouping from valid FileRecord objects."""
    if not records:
        return ContextualGrouping(groups=())

    ordered_records = _sort_records_for_grouping(records)
    record_root = _record_root(ordered_records)
    groups = _build_contextual_groups(ordered_records, record_root)
    return ContextualGrouping(groups=tuple(sorted(groups, key=lambda group: group.group_id)))


def _sort_records_for_grouping(records: tuple[FileRecord, ...]) -> tuple[FileRecord, ...]:
    return tuple(
        sorted(
            records,
            key=lambda record: (record.timestamp, str(record.path)),
        )
    )


def _build_contextual_groups(
    ordered_records: tuple[FileRecord, ...],
    record_root: Path,
) -> list[ContextualGroup]:
    groups: list[ContextualGroup] = []
    current_group_records: list[FileRecord] = [ordered_records[0]]

    for previous_record, current_record in zip(ordered_records, ordered_records[1:]):
        if _are_adjacent(previous_record, current_record):
            current_group_records.append(current_record)
            continue

        groups.append(_make_contextual_group(tuple(current_group_records), record_root))
        current_group_records = [current_record]

    groups.append(_make_contextual_group(tuple(current_group_records), record_root))
    return groups


def _are_adjacent(previous_record: FileRecord, current_record: FileRecord) -> bool:
    delta_seconds = (current_record.timestamp - previous_record.timestamp).total_seconds()
    return delta_seconds <= TIME_WINDOW_SECONDS


def _record_root(records: tuple[FileRecord, ...]) -> Path:
    return Path(os.path.commonpath([str(record.path.parent) for record in records]))


def _make_contextual_group(
    records: tuple[FileRecord, ...], record_root: Path
) -> ContextualGroup:
    member_refs = tuple(
        sorted(record.path.relative_to(record_root).as_posix() for record in records)
    )
    return ContextualGroup(
        group_id=compute_group_id(member_refs),
        member_refs=member_refs,
    )
