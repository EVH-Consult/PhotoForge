# src/photoforge/scanner.py

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Callable, Iterable

from .hashing import compute_sha256
from .media_formats import (
    CANONICAL_EXTENSION,
    LIVE_PHOTO_STILL_FORMATS,
    media_format_for,
    validate_media_file,
)
from .metadata import normalize_metadata
from .metadata_extractors import (
    ExifContext,
    extract_exif_context,
    extract_exif_diagnostics,
    extract_filename_timestamp,
    extract_folder_timestamp,
    extract_heic_timestamp,
    extract_jpeg_timestamp,
    extract_png_timestamp,
    extract_raw_timestamp,
    extract_tiff_timestamp,
    extract_video_timestamp,
    extract_xmp_metadata,
)
from .model import (
    BatchContext,
    ExtractionDiagnostic,
    FileMetadataDiagnostics,
    FileRecord,
    MediaMetadata,
    TimestampCandidate,
)
from .timestamp_diagnostics import build_metadata_diagnostics
from .timestamp_policy import (
    AppliedTimestampPolicy,
    PolicyContext,
    TimestampPolicy,
    apply_timestamp_policy,
)
from .timestamp_resolution import resolve_timestamp_candidates

TimestampExtractor = Callable[[Path, float], tuple[TimestampCandidate, ...]]

EXTRACTOR_MAP: dict[str, TimestampExtractor] = {
    ".jpg": extract_jpeg_timestamp,
    ".jpeg": extract_jpeg_timestamp,
    ".png": extract_png_timestamp,
    ".heic": extract_heic_timestamp,
    ".heif": extract_heic_timestamp,
    ".cr2": extract_raw_timestamp,
    ".nef": extract_raw_timestamp,
    ".arw": extract_raw_timestamp,
    ".mp4": extract_video_timestamp,
    ".mov": extract_video_timestamp,
    ".tif": extract_tiff_timestamp,
    ".tiff": extract_tiff_timestamp,
}

SUPPORTED_EXTENSIONS = set(EXTRACTOR_MAP)


@dataclass(frozen=True)
class SkippedFile:
    path: Path
    reason: str


@dataclass(frozen=True)
class ScanIssue:
    path: Path
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class ScanResult:
    records: tuple[FileRecord, ...]
    skipped: tuple[SkippedFile, ...]
    issues: tuple[ScanIssue, ...]
    total_entries_seen: int
    supported_files_processed: int
    metadata_diagnostics: tuple[FileMetadataDiagnostics, ...] = ()
    batch_contexts: tuple[BatchContext, ...] = ()


@dataclass(frozen=True)
class _PreparedMedia:
    path: Path
    size: int
    candidates: tuple[TimestampCandidate, ...]
    extraction_diagnostics: tuple[ExtractionDiagnostic, ...]
    camera_make: str | None
    camera_model: str | None
    keywords: tuple[str, ...]
    gps_latitude: float | None
    gps_longitude: float | None
    xmp_sidecar: Path | None
    sha256: str


def normalize_path(path: Path) -> Path:
    return path.resolve(strict=True)


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def discover_files(input_path: Path) -> tuple[Path, ...]:
    discovered: list[Path] = []

    for root, dirnames, filenames in os.walk(input_path, topdown=True, followlinks=False):
        dirnames.sort()
        filenames.sort()

        root_path = Path(root)
        for filename in filenames:
            # Keep the lexical path until symlink classification. Resolving here
            # would follow a file symlink before ``is_symlink`` can reject it.
            discovered.append(root_path / filename)

    return tuple(discovered)


def get_file_size_and_mtime(path: Path) -> tuple[int, float]:
    stat_result = path.stat()
    return stat_result.st_size, stat_result.st_mtime


def scan_directory(
    input_path: Path,
    *,
    timestamp_policy: TimestampPolicy | None = None,
) -> ScanResult:
    root_path = _validate_input_directory(input_path)
    discovered_paths = discover_files(root_path)
    policy = timestamp_policy or TimestampPolicy()

    records: list[FileRecord] = []
    prepared_media: list[_PreparedMedia] = []
    skipped: list[SkippedFile] = []
    issues: list[ScanIssue] = []
    metadata_diagnostics: list[FileMetadataDiagnostics] = []

    for path in discovered_paths:
        if path.is_symlink():
            skipped.append(SkippedFile(path=path, reason="symlink"))
            continue

        if not path.is_file():
            skipped.append(SkippedFile(path=path, reason="not_regular_file"))
            continue

        if not is_supported_file(path):
            skipped.append(SkippedFile(path=path, reason="unsupported_extension"))
            continue

        ext = path.suffix.lower()
        extractor = EXTRACTOR_MAP[ext]
        media_format = media_format_for(path)
        assert media_format is not None

        try:
            size, mtime_timestamp = get_file_size_and_mtime(path)
        except OSError as exc:
            _record_corrupt_file(
                skipped=skipped,
                issues=issues,
                path=path,
                reason="corrupt_metadata_unreadable",
                code="corrupt_metadata_unreadable",
                message=str(exc),
            )
            continue

        # JPEG validation remains on its established metadata/fallback path.
        # Newly introduced formats use an explicit structural gate so their
        # corrupt behavior is defined without changing legacy JPEG outcomes.
        if media_format != "jpeg":
            try:
                validate_media_file(path, media_format)
            except ValueError as exc:
                _record_corrupt_file(
                    skipped=skipped,
                    issues=issues,
                    path=path,
                    reason="corrupt_metadata_unreadable",
                    code="corrupt_metadata_unreadable",
                    message=str(exc),
                )
                continue

        try:
            format_candidates = extractor(path, mtime_timestamp)
            filename_candidates = extract_filename_timestamp(path.name)
            folder_candidates = extract_folder_timestamp(path.parent.name)
            xmp_metadata = extract_xmp_metadata(path)
            extracted_candidates = (
                *format_candidates,
                *xmp_metadata.timestamp_candidates,
                *filename_candidates,
                *folder_candidates,
            )

            exif_diagnostics = ()
            if ext in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
                exif_context = extract_exif_context(path)
                exif_diagnostics = extract_exif_diagnostics(path)
            else:
                exif_context = ExifContext(None, None, (), None, None)
            extraction_diagnostics = (
                *exif_diagnostics,
                *xmp_metadata.diagnostics,
            )
        except Exception as exc:
            _record_corrupt_file(
                skipped=skipped,
                issues=issues,
                path=path,
                reason="corrupt_timestamp_unresolved",
                code="corrupt_timestamp_unresolved",
                message=str(exc),
            )
            continue

        try:
            sha256 = compute_sha256(path)
        except OSError as exc:
            _record_corrupt_file(
                skipped=skipped,
                issues=issues,
                path=path,
                reason="corrupt_file_unreadable",
                code="corrupt_file_unreadable",
                message=str(exc),
            )
            continue
        except Exception as exc:
            _record_corrupt_file(
                skipped=skipped,
                issues=issues,
                path=path,
                reason="corrupt_hash_failed",
                code="corrupt_hash_failed",
                message=str(exc),
            )
            continue

        gps_latitude = exif_context.gps_latitude
        gps_longitude = exif_context.gps_longitude
        if gps_latitude is None:
            gps_latitude = xmp_metadata.gps_latitude
            gps_longitude = xmp_metadata.gps_longitude

        prepared_media.append(
            _PreparedMedia(
                path=path,
                size=size,
                candidates=tuple(extracted_candidates),
                extraction_diagnostics=tuple(extraction_diagnostics),
                camera_make=exif_context.camera_make,
                camera_model=exif_context.camera_model,
                keywords=tuple(
                    sorted(
                        {*exif_context.keywords, *xmp_metadata.keywords},
                        key=lambda value: (value.casefold(), value),
                    )
                ),
                gps_latitude=gps_latitude,
                gps_longitude=gps_longitude,
                xmp_sidecar=xmp_metadata.path,
                sha256=sha256,
            )
        )

    trusted_device_offsets = _trusted_device_offsets(prepared_media)
    inconsistent_paths: set[Path] = set()

    for prepared in prepared_media:
        relative_folder = prepared.path.parent.relative_to(root_path).as_posix()
        device_key = _device_key(prepared.camera_make, prepared.camera_model)
        context = PolicyContext(
            relative_folder="" if relative_folder == "." else relative_folder,
            camera_make=prepared.camera_make,
            camera_model=prepared.camera_model,
            gps_latitude=prepared.gps_latitude,
            gps_longitude=prepared.gps_longitude,
            trusted_device_offset=(
                trusted_device_offsets.get(device_key) if device_key is not None else None
            ),
        )
        applied = tuple(
            apply_timestamp_policy(candidate, policy, context)
            for candidate in prepared.candidates
        )
        applied_candidates = tuple(item.candidate for item in applied)

        try:
            resolution_result = resolve_timestamp_candidates(applied_candidates)
            diagnostics = build_metadata_diagnostics(
                resolution_result.valid_candidates,
                extraction_diagnostics=prepared.extraction_diagnostics,
            )
            normalized_metadata = normalize_metadata(resolution_result.primary_candidate)
        except Exception as exc:
            _record_corrupt_file(
                skipped=skipped,
                issues=issues,
                path=prepared.path,
                reason="corrupt_timestamp_unresolved",
                code="corrupt_timestamp_unresolved",
                message=str(exc),
            )
            continue

        selected_policy = _selected_policy(applied, resolution_result.primary_candidate)
        media_metadata = MediaMetadata(
            timestamp_candidates=resolution_result.valid_candidates,
            selected_candidate=resolution_result.primary_candidate,
            camera_make=prepared.camera_make,
            camera_model=prepared.camera_model,
            keywords=prepared.keywords,
            gps_latitude=prepared.gps_latitude,
            gps_longitude=prepared.gps_longitude,
            xmp_sidecar=prepared.xmp_sidecar,
            timezone_basis=selected_policy.timezone_basis,
            clock_correction=selected_policy.clock_correction,
        )
        records.append(
            FileRecord(
                path=prepared.path,
                size=prepared.size,
                timestamp=normalized_metadata.timestamp,
                timestamp_source=normalized_metadata.timestamp_source,
                sha256=prepared.sha256,
                short_hash=prepared.sha256[:8],
                metadata=media_metadata,
                media_format=media_format_for(prepared.path) or "",
                canonical_extension=CANONICAL_EXTENSION[
                    media_format_for(prepared.path) or ""
                ],
            )
        )

        if diagnostics.has_inconsistency:
            inconsistent_paths.add(prepared.path)
        if diagnostics.extraction_diagnostics or diagnostics.comparisons:
            metadata_diagnostics.append(
                FileMetadataDiagnostics(
                    path=prepared.path,
                    metadata_diagnostics=diagnostics,
                )
            )

    records, live_photo_issues = _annotate_live_photos(records, root_path)
    issues.extend(live_photo_issues)
    batch_contexts = _build_batch_contexts(records, inconsistent_paths)

    return ScanResult(
        records=tuple(records),
        skipped=tuple(_sorted_skipped(skipped)),
        issues=tuple(_sorted_issues(issues)),
        total_entries_seen=len(discovered_paths),
        supported_files_processed=len(records),
        metadata_diagnostics=tuple(metadata_diagnostics),
        batch_contexts=batch_contexts,
    )


def _annotate_live_photos(
    records: list[FileRecord],
    root_path: Path,
) -> tuple[list[FileRecord], list[ScanIssue]]:
    grouped: dict[tuple[Path, str], list[int]] = {}
    for index, record in enumerate(records):
        if record.media_format not in LIVE_PHOTO_STILL_FORMATS | {"mov"}:
            continue
        grouped.setdefault((record.path.parent, record.path.stem), []).append(index)

    annotated = list(records)
    issues: list[ScanIssue] = []
    for _, indexes in sorted(
        grouped.items(), key=lambda item: (str(item[0][0]), item[0][1])
    ):
        still_indexes = [
            index
            for index in indexes
            if records[index].media_format in LIVE_PHOTO_STILL_FORMATS
        ]
        motion_indexes = [
            index for index in indexes if records[index].media_format == "mov"
        ]
        if not motion_indexes or not still_indexes:
            continue
        if len(still_indexes) != 1 or len(motion_indexes) != 1:
            for index in indexes:
                issues.append(
                    ScanIssue(
                        path=records[index].path,
                        severity="warning",
                        code="ambiguous_live_photo_pair",
                        message=(
                            "Live Photo pairing requires exactly one JPEG/HEIC/HEIF "
                            "still and one MOV with the same case-sensitive stem in "
                            "the same directory"
                        ),
                    )
                )
            continue

        still_index = still_indexes[0]
        motion_index = motion_indexes[0]
        still_ref = records[still_index].path.relative_to(root_path).as_posix()
        motion_ref = records[motion_index].path.relative_to(root_path).as_posix()
        pair_id = hashlib.sha256(
            f"{still_ref}\0{motion_ref}".encode("utf-8")
        ).hexdigest()
        annotated[still_index] = replace(
            records[still_index],
            live_photo_pair_id=pair_id,
            live_photo_role="still",
        )
        annotated[motion_index] = replace(
            records[motion_index],
            live_photo_pair_id=pair_id,
            live_photo_role="motion",
        )

    return annotated, issues


def _device_key(make: str | None, model: str | None) -> tuple[str, str] | None:
    if make is None or model is None:
        return None
    return make, model


def _trusted_device_offsets(
    prepared_media: list[_PreparedMedia],
) -> dict[tuple[str, str], timedelta]:
    candidates: dict[tuple[str, str], set[timedelta]] = {}
    for prepared in prepared_media:
        key = _device_key(prepared.camera_make, prepared.camera_model)
        if key is None:
            continue
        for candidate in prepared.candidates:
            if (
                candidate.source_kind in {"exif", "xmp"}
                and candidate.timezone_offset is not None
            ):
                candidates.setdefault(key, set()).add(candidate.timezone_offset)
    return {
        key: next(iter(offsets))
        for key, offsets in candidates.items()
        if len(offsets) == 1
    }


def _selected_policy(
    applied: tuple[AppliedTimestampPolicy, ...],
    selected: TimestampCandidate,
) -> AppliedTimestampPolicy:
    for item in applied:
        if item.candidate == selected:
            return item
    raise ValueError("selected timestamp policy result is missing")


def _build_batch_contexts(
    records: list[FileRecord],
    inconsistent_paths: set[Path],
) -> tuple[BatchContext, ...]:
    grouped: dict[Path, list[FileRecord]] = {}
    for record in records:
        grouped.setdefault(record.path.parent, []).append(record)

    contexts: list[BatchContext] = []
    for folder in sorted(grouped, key=str):
        members = grouped[folder]
        timestamps = sorted(record.timestamp for record in members)
        if len(members) < 2:
            classification = "insufficient_evidence"
        elif timestamps[-1] - timestamps[0] <= timedelta(hours=24):
            classification = "event_bounded"
        else:
            classification = "mixed_content"
        contexts.append(
            BatchContext(
                folder=folder,
                classification=classification,
                member_count=len(members),
                earliest_timestamp=timestamps[0],
                latest_timestamp=timestamps[-1],
                has_source_inconsistency=any(
                    member.path in inconsistent_paths for member in members
                ),
            )
        )
    return tuple(contexts)


def _record_corrupt_file(
    skipped: list[SkippedFile],
    issues: list[ScanIssue],
    path: Path,
    reason: str,
    code: str,
    message: str,
) -> None:
    skipped.append(SkippedFile(path=path, reason=reason))
    issues.append(
        ScanIssue(
            path=path,
            severity="error",
            code=code,
            message=message,
        )
    )


def _validate_input_directory(input_path: Path) -> Path:
    try:
        normalized = normalize_path(input_path)
    except FileNotFoundError as exc:
        raise ValueError(f"Input path does not exist: {input_path}") from exc
    except OSError as exc:
        raise ValueError(f"Input path is not accessible: {input_path}") from exc

    if not normalized.is_dir():
        raise ValueError(f"Input path is not a directory: {normalized}")

    return normalized


def _sorted_skipped(items: Iterable[SkippedFile]) -> list[SkippedFile]:
    return sorted(items, key=lambda item: str(item.path))


def _sorted_issues(items: Iterable[ScanIssue]) -> list[ScanIssue]:
    return sorted(items, key=lambda item: (str(item.path), item.code))
