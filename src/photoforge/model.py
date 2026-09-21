# src/photoforge/model.py

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class TimestampCandidate:
    source_kind: str
    source_detail: str
    naive_timestamp: datetime
    precision: str
    timezone_offset: timedelta | None = None

    def __post_init__(self) -> None:
        if self.source_kind == "":
            raise ValueError("source_kind must not be empty")

        if self.source_detail == "":
            raise ValueError("source_detail must not be empty")

        if self.naive_timestamp.tzinfo is not None:
            raise ValueError("naive_timestamp must be naive")

        if self.precision not in {"date", "datetime"}:
            raise ValueError("precision must be 'date' or 'datetime'")

    @property
    def aware_timestamp(self) -> datetime | None:
        if self.timezone_offset is None:
            return None
        return self.naive_timestamp.replace(tzinfo=timezone(self.timezone_offset))

    @property
    def utc_timestamp(self) -> datetime | None:
        aware = self.aware_timestamp
        if aware is None:
            return None
        return aware.astimezone(timezone.utc)


@dataclass(frozen=True)
class MediaMetadata:
    timestamp_candidates: tuple[TimestampCandidate, ...]
    selected_candidate: TimestampCandidate
    camera_make: str | None = None
    camera_model: str | None = None
    keywords: tuple[str, ...] = ()
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    xmp_sidecar: Path | None = None
    timezone_basis: str | None = None
    clock_correction: timedelta | None = None

    def __post_init__(self) -> None:
        if self.selected_candidate not in self.timestamp_candidates:
            raise ValueError("selected_candidate must be present in timestamp_candidates")

        if (self.gps_latitude is None) != (self.gps_longitude is None):
            raise ValueError("GPS latitude and longitude must be provided together")

        if self.gps_latitude is not None and not -90 <= self.gps_latitude <= 90:
            raise ValueError("gps_latitude must be between -90 and 90")

        if self.gps_longitude is not None and not -180 <= self.gps_longitude <= 180:
            raise ValueError("gps_longitude must be between -180 and 180")


@dataclass(frozen=True)
class TimestampResolutionResult:
    primary_candidate: TimestampCandidate
    valid_candidates: tuple[TimestampCandidate, ...]

    def __post_init__(self) -> None:
        if not self.valid_candidates:
            raise ValueError("valid_candidates must not be empty")

        if self.primary_candidate != self.valid_candidates[0]:
            raise ValueError(
                "primary_candidate must be the first item in valid_candidates"
            )


@dataclass(frozen=True)
class TimestampComparison:
    left_source: str
    right_source: str
    representation: str
    left_value: datetime
    right_value: datetime
    equal: bool

    def __post_init__(self) -> None:
        if self.left_source == "":
            raise ValueError("left_source must not be empty")

        if self.right_source == "":
            raise ValueError("right_source must not be empty")

        if self.representation not in {"utc", "naive"}:
            raise ValueError("representation must be 'utc' or 'naive'")


@dataclass(frozen=True)
class FileRecord:
    path: Path
    size: int
    timestamp: datetime
    timestamp_source: str
    sha256: str
    short_hash: str
    metadata: MediaMetadata | None = None
    media_format: str = "jpeg"
    canonical_extension: str = ".jpg"
    live_photo_pair_id: str | None = None
    live_photo_role: str | None = None


@dataclass(frozen=True)
class CorruptFile:
    path: Path
    error_type: str


@dataclass(frozen=True)
class PlannedRecord:
    path: Path
    duplicate_group_id: str
    duplicate_group_size: int
    canonical: bool
    canonical_filename: str
    target_path: Path | None
    action_status: str
    sha256: str
    short_hash: str
    timestamp: datetime
    timestamp_source: str
    metadata: MediaMetadata | None = None
    media_format: str = "jpeg"
    live_photo_pair_id: str | None = None
    live_photo_role: str | None = None


@dataclass(frozen=True)
class PlannedAction:
    source_path: Path
    target_path: Path
    action: str


@dataclass(frozen=True)
class PlanResult:
    records: tuple[PlannedRecord, ...]
    actions: tuple[PlannedAction, ...]
    corrupt_files: tuple[CorruptFile, ...]
    batch_contexts: tuple[BatchContext, ...] = ()


@dataclass(frozen=True)
class BatchContext:
    folder: Path
    classification: str
    member_count: int
    earliest_timestamp: datetime
    latest_timestamp: datetime
    has_source_inconsistency: bool

    def __post_init__(self) -> None:
        if self.classification not in {
            "event_bounded",
            "mixed_content",
            "insufficient_evidence",
        }:
            raise ValueError("unsupported batch classification")
        if self.member_count < 1:
            raise ValueError("member_count must be positive")
        if self.latest_timestamp < self.earliest_timestamp:
            raise ValueError("latest_timestamp must not precede earliest_timestamp")


@dataclass(frozen=True)
class ContextualGroup:
    group_id: str
    member_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        validate_member_refs(self.member_refs)

        expected_group_id = compute_group_id(self.member_refs)
        if self.group_id != expected_group_id:
            raise ValueError(
                "ContextualGroup.group_id does not match the computed group_id"
            )


@dataclass(frozen=True)
class ContextualGrouping:
    groups: tuple[ContextualGroup, ...]

    def __post_init__(self) -> None:
        group_ids = tuple(group.group_id for group in self.groups)

        if len(set(group_ids)) != len(group_ids):
            raise ValueError(
                "ContextualGrouping.groups must contain unique group_id values"
            )

        sorted_group_ids = tuple(sorted(group_ids))
        if group_ids != sorted_group_ids:
            raise ValueError(
                "ContextualGrouping.groups must be sorted lexicographically by group_id"
            )


def to_record_ref(file_record: FileRecord) -> str:
    return str(file_record.path)


def validate_record_ref(record_ref: str) -> None:
    if record_ref == "":
        raise ValueError("record_ref must not be empty")


def _encode_member_refs(member_refs: tuple[str, ...]) -> bytes:
    return json.dumps(
        member_refs,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_group_id(member_refs: tuple[str, ...]) -> str:
    """Compute deterministic group_id from canonical JSON encoding of member_refs."""
    validate_member_refs(member_refs)
    canonical_json = _encode_member_refs(member_refs)
    return hashlib.sha256(canonical_json).hexdigest()


def validate_member_refs(member_refs: tuple[str, ...]) -> None:
    if not member_refs:
        raise ValueError("member_refs must not be empty")

    for record_ref in member_refs:
        validate_record_ref(record_ref)

    sorted_member_refs = tuple(sorted(member_refs))
    if member_refs != sorted_member_refs:
        raise ValueError("member_refs must be sorted lexicographically")

    if len(set(member_refs)) != len(member_refs):
        raise ValueError("member_refs must contain unique record_ref values")


def validate_contextual_group(group: ContextualGroup) -> None:
    validate_member_refs(group.member_refs)

    expected_group_id = compute_group_id(group.member_refs)
    if group.group_id != expected_group_id:
        raise ValueError(
            "ContextualGroup.group_id must match the deterministic group_id computed from member_refs"
        )


def validate_contextual_grouping(grouping: ContextualGrouping) -> None:
    group_ids = tuple(group.group_id for group in grouping.groups)

    if len(set(group_ids)) != len(group_ids):
        raise ValueError(
            "ContextualGrouping.groups must contain unique group_id values"
        )

    sorted_group_ids = tuple(sorted(group_ids))
    if group_ids != sorted_group_ids:
        raise ValueError(
            "ContextualGrouping.groups must be sorted lexicographically by group_id"
        )

    seen_record_refs: set[str] = set()
    for group in grouping.groups:
        validate_contextual_group(group)

        overlapping_record_refs = seen_record_refs.intersection(group.member_refs)
        if overlapping_record_refs:
            raise ValueError(
                "ContextualGrouping.groups must not contain duplicate record_ref values across groups"
            )

        seen_record_refs.update(group.member_refs)


@dataclass(frozen=True)
class ExtractionDiagnostic:
    source_kind: str
    diagnostic_type: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        if self.source_kind == "":
            raise ValueError("source_kind must not be empty")

        if self.diagnostic_type not in {"missing", "unreadable", "invalid"}:
            raise ValueError(
                "diagnostic_type must be 'missing', 'unreadable', or 'invalid'"
            )

        if self.field_name == "":
            raise ValueError("field_name must not be empty when provided")


@dataclass(frozen=True)
class MetadataDiagnostics:
    extraction_diagnostics: tuple[ExtractionDiagnostic, ...]
    comparisons: tuple[TimestampComparison, ...]
    inconsistent_pairs: tuple[TimestampComparison, ...]

    def __post_init__(self) -> None:
        comparison_set = set(self.comparisons)
        for comparison in self.inconsistent_pairs:
            if comparison not in comparison_set:
                raise ValueError(
                    "inconsistent_pairs must be a subset of comparisons"
                )

    @property
    def has_inconsistency(self) -> bool:
        return bool(self.inconsistent_pairs)

    @property
    def has_extraction_diagnostics(self) -> bool:
        return bool(self.extraction_diagnostics)


@dataclass(frozen=True)
class FileMetadataDiagnostics:
    path: Path
    metadata_diagnostics: MetadataDiagnostics
