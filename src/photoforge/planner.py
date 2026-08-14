from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .model import FileRecord, PlanResult, PlannedAction, PlannedRecord, CorruptFile


def _sorted_records(records: Iterable[FileRecord]) -> list[FileRecord]:
    return sorted(records, key=lambda record: str(record.path))


def _group_by_sha256(records: list[FileRecord]) -> list[tuple[str, list[FileRecord]]]:
    grouped: dict[str, list[FileRecord]] = defaultdict(list)

    for record in records:
        grouped[record.sha256].append(record)

    groups: list[tuple[str, list[FileRecord]]] = []
    for sha256 in sorted(grouped):
        group_records = sorted(grouped[sha256], key=lambda record: str(record.path))
        groups.append((sha256, group_records))

    return groups


def _canonical_ranking_key(record: FileRecord) -> tuple[int, int, str]:
    exif_priority = 0 if record.timestamp_source.startswith("exif_") else 1
    return (-record.size, exif_priority, str(record.path))


def _select_canonical(group_records: list[FileRecord]) -> FileRecord:
    return min(group_records, key=_canonical_ranking_key)


def _build_canonical_filename(record: FileRecord) -> str:
    timestamp_part = record.timestamp.strftime("%Y-%m-%d_%H%M%S")
    return f"{timestamp_part}_{record.short_hash}.jpg"


def _resolve_target_path(
    source_path: Path,
    canonical_filename: str,
    timestamp_year: str,
    timestamp_month: str,
    timestamp_day: str,
    output_path: Path | None,
) -> Path:
    if output_path is None:
        return source_path.parent / canonical_filename

    return output_path / timestamp_year / timestamp_month / timestamp_day / canonical_filename


def _classify_action(
    source_path: Path,
    target_path: Path,
    output_path: Path | None,
    reserved_targets: set[Path],
) -> str:
    if source_path == target_path:
        return "skip"
    if target_path.exists() or target_path in reserved_targets:
        return "collision"
    if output_path is None:
        return "rename"
    return "move"


def plan_files(
    records: Iterable[FileRecord],
    output_path: Path | None = None,
    corrupt_files: Iterable[CorruptFile] = (),
) -> PlanResult:
    sorted_records = _sorted_records(records)
    grouped_records = _group_by_sha256(sorted_records)

    planned_records: list[PlannedRecord] = []
    planned_actions: list[PlannedAction] = []
    reserved_targets: set[Path] = set()

    for sha256, group_records in grouped_records:
        canonical_record = _select_canonical(group_records)
        canonical_filename = _build_canonical_filename(canonical_record)
        timestamp_year = canonical_record.timestamp.strftime("%Y")
        timestamp_month = canonical_record.timestamp.strftime("%m")
        timestamp_day = canonical_record.timestamp.strftime("%d")
        duplicate_group_size = len(group_records)

        canonical_target_path = _resolve_target_path(
            source_path=canonical_record.path,
            canonical_filename=canonical_filename,
            timestamp_year=timestamp_year,
            timestamp_month=timestamp_month,
            timestamp_day=timestamp_day,
            output_path=output_path,
        )
        canonical_action_status = _classify_action(
            source_path=canonical_record.path,
            target_path=canonical_target_path,
            output_path=output_path,
            reserved_targets=reserved_targets,
        )
        if canonical_action_status not in {"skip", "collision"}:
            reserved_targets.add(canonical_target_path)

        for record in group_records:
            is_canonical = record.path == canonical_record.path

            if is_canonical:
                target_path: Path | None = canonical_target_path
                action_status = canonical_action_status
                planned_actions.append(
                    PlannedAction(
                        source_path=record.path,
                        target_path=canonical_target_path,
                        action=canonical_action_status,
                    )
                )
            else:
                target_path = None
                action_status = "duplicate"

            planned_records.append(
                PlannedRecord(
                    path=record.path,
                    duplicate_group_id=sha256,
                    duplicate_group_size=duplicate_group_size,
                    canonical=is_canonical,
                    canonical_filename=canonical_filename,
                    target_path=target_path,
                    action_status=action_status,
                    sha256=record.sha256,
                    short_hash=record.short_hash,
                    timestamp=record.timestamp,
                    timestamp_source=record.timestamp_source,
                )
            )

    return PlanResult(
        records=tuple(planned_records),
        actions=tuple(planned_actions),
        corrupt_files=tuple(sorted(
            corrupt_files, key=lambda c: str(c.path)
        )),
    )
