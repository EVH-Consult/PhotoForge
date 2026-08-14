# src/photoforge/scanner.py

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .hashing import compute_sha256
from .metadata import normalize_metadata
from .metadata_extractors import (
    extract_exif_diagnostics,
    extract_heic_timestamp,
    extract_jpeg_timestamp,
    extract_png_timestamp,
    extract_raw_timestamp,
    extract_video_timestamp,
)
from .model import FileMetadataDiagnostics, FileRecord, TimestampCandidate
from .timestamp_diagnostics import build_metadata_diagnostics
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
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg"}
RECOGNIZED_EXTENSIONS = set(EXTRACTOR_MAP) - SUPPORTED_EXTENSIONS


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


def scan_directory(input_path: Path) -> ScanResult:
    root_path = _validate_input_directory(input_path)
    discovered_paths = discover_files(root_path)

    records: list[FileRecord] = []
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
            reason = (
                "recognized_not_processable"
                if path.suffix.lower() in RECOGNIZED_EXTENSIONS
                else "unsupported_extension"
            )
            skipped.append(SkippedFile(path=path, reason=reason))
            continue

        ext = path.suffix.lower()
        extractor = EXTRACTOR_MAP[ext]

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

        try:
            format_candidates = extractor(path, mtime_timestamp)
            extracted_candidates = format_candidates

            exif_diagnostics = ()
            if ext in {".jpg", ".jpeg"}:
                exif_diagnostics = extract_exif_diagnostics(path)

            resolution_result = resolve_timestamp_candidates(extracted_candidates)
            diagnostics = build_metadata_diagnostics(
                resolution_result.valid_candidates,
                extraction_diagnostics=exif_diagnostics,
            )
            normalized_metadata = normalize_metadata(resolution_result.primary_candidate)
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

        records.append(
            FileRecord(
                path=path,
                size=size,
                timestamp=normalized_metadata.timestamp,
                timestamp_source=normalized_metadata.timestamp_source,
                sha256=sha256,
                short_hash=sha256[:8],
            )
        )

        if diagnostics.extraction_diagnostics or diagnostics.comparisons:
            metadata_diagnostics.append(
                FileMetadataDiagnostics(
                    path=path,
                    metadata_diagnostics=diagnostics,
                )
            )

    return ScanResult(
        records=tuple(records),
        skipped=tuple(_sorted_skipped(skipped)),
        issues=tuple(_sorted_issues(issues)),
        total_entries_seen=len(discovered_paths),
        supported_files_processed=len(records),
        metadata_diagnostics=tuple(metadata_diagnostics),
    )


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
