from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .model import (
    CorruptFile,
    FileRecord,
    PlannedAction,
    PlannedRecord,
    PlanResult,
)


def _sorted_records(records: Iterable[FileRecord]) -> list[FileRecord]:
    return sorted(records, key=lambda record: str(record.path))


@dataclass(frozen=True)
class _MediaAsset:
    asset_hash: str
    records: tuple[FileRecord, ...]

    @property
    def primary(self) -> FileRecord:
        return next(
            (record for record in self.records if record.live_photo_role == "still"),
            self.records[0],
        )

    @property
    def size(self) -> int:
        return sum(record.size for record in self.records)


def _build_assets(records: list[FileRecord]) -> list[_MediaAsset]:
    paired: dict[str, list[FileRecord]] = defaultdict(list)
    unpaired: list[FileRecord] = []
    for record in records:
        if record.live_photo_pair_id is None:
            unpaired.append(record)
        else:
            paired[record.live_photo_pair_id].append(record)

    assets = [_MediaAsset(record.sha256, (record,)) for record in unpaired]
    for pair_id in sorted(paired):
        components = tuple(
            sorted(
                paired[pair_id],
                key=lambda item: (item.live_photo_role != "still", str(item.path)),
            )
        )
        if len(components) != 2 or {item.live_photo_role for item in components} != {
            "still",
            "motion",
        }:
            raise ValueError("invalid Live Photo pair in planner input")
        digest = hashlib.sha256(
            f"{components[0].sha256}\0{components[1].sha256}".encode("ascii")
        ).hexdigest()
        assets.append(_MediaAsset(digest, components))
    return sorted(
        assets,
        key=lambda asset: tuple(str(item.path) for item in asset.records),
    )


def _group_assets(assets: list[_MediaAsset]) -> list[tuple[str, list[_MediaAsset]]]:
    grouped: dict[str, list[_MediaAsset]] = defaultdict(list)

    for asset in assets:
        grouped[asset.asset_hash].append(asset)

    groups: list[tuple[str, list[_MediaAsset]]] = []
    for asset_hash in sorted(grouped):
        group_assets = sorted(
            grouped[asset_hash],
            key=lambda asset: tuple(str(record.path) for record in asset.records),
        )
        groups.append((asset_hash, group_assets))

    return groups


def _canonical_ranking_key(asset: _MediaAsset) -> tuple[int, int, tuple[str, ...]]:
    exif_priority = 0 if asset.primary.timestamp_source.startswith("exif_") else 1
    return (
        -asset.size,
        exif_priority,
        tuple(str(record.path) for record in asset.records),
    )


def _select_canonical(group_assets: list[_MediaAsset]) -> _MediaAsset:
    return min(group_assets, key=_canonical_ranking_key)


def _build_canonical_basename(asset: _MediaAsset) -> str:
    timestamp_part = asset.primary.timestamp.strftime("%Y-%m-%d_%H%M%S")
    return f"{timestamp_part}_{asset.asset_hash[:8]}"


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
    grouped_assets = _group_assets(_build_assets(sorted_records))

    planned_records: list[PlannedRecord] = []
    planned_actions: list[PlannedAction] = []
    reserved_targets: set[Path] = set()

    for asset_hash, group in grouped_assets:
        canonical_asset = _select_canonical(group)
        canonical_basename = _build_canonical_basename(canonical_asset)
        timestamp_year = canonical_asset.primary.timestamp.strftime("%Y")
        timestamp_month = canonical_asset.primary.timestamp.strftime("%m")
        timestamp_day = canonical_asset.primary.timestamp.strftime("%d")
        duplicate_group_size = len(group)
        canonical_filenames = {
            record.live_photo_role: f"{canonical_basename}{record.canonical_extension}"
            for record in canonical_asset.records
        }
        if len(canonical_asset.records) == 1:
            canonical_filenames[None] = (
                f"{canonical_basename}{canonical_asset.records[0].canonical_extension}"
            )

        targets = {
            record.path: _resolve_target_path(
                source_path=record.path,
                canonical_filename=canonical_filenames[record.live_photo_role],
                timestamp_year=timestamp_year,
                timestamp_month=timestamp_month,
                timestamp_day=timestamp_day,
                output_path=output_path,
            )
            for record in canonical_asset.records
        }
        has_collision = any(
            (target.exists() and target != source) or target in reserved_targets
            for source, target in targets.items()
        )

        for asset in group:
            is_canonical_asset = asset is canonical_asset
            for record in asset.records:
                canonical_filename = canonical_filenames[record.live_photo_role]
                if is_canonical_asset:
                    target_path: Path | None = targets[record.path]
                    action_status = (
                        "collision"
                        if has_collision
                        else _classify_action(
                            source_path=record.path,
                            target_path=target_path,
                            output_path=output_path,
                            reserved_targets=reserved_targets,
                        )
                    )
                    planned_actions.append(
                        PlannedAction(
                            source_path=record.path,
                            target_path=target_path,
                            action=action_status,
                        )
                    )
                    if action_status not in {"skip", "collision"}:
                        reserved_targets.add(target_path)
                else:
                    target_path = None
                    action_status = "duplicate"

                planned_records.append(
                    PlannedRecord(
                        path=record.path,
                        duplicate_group_id=asset_hash,
                        duplicate_group_size=duplicate_group_size,
                        canonical=is_canonical_asset,
                        canonical_filename=canonical_filename,
                        target_path=target_path,
                        action_status=action_status,
                        sha256=record.sha256,
                        short_hash=record.short_hash,
                        timestamp=record.timestamp,
                        timestamp_source=record.timestamp_source,
                        metadata=record.metadata,
                        media_format=record.media_format,
                        live_photo_pair_id=record.live_photo_pair_id,
                        live_photo_role=record.live_photo_role,
                    )
                )

    return PlanResult(
        records=tuple(planned_records),
        actions=tuple(planned_actions),
        corrupt_files=tuple(sorted(
            corrupt_files, key=lambda c: str(c.path)
        )),
    )
