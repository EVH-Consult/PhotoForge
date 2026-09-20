from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree

from ..model import ExtractionDiagnostic, TimestampCandidate


@dataclass(frozen=True)
class XmpMetadata:
    path: Path | None
    timestamp_candidates: tuple[TimestampCandidate, ...]
    keywords: tuple[str, ...]
    gps_latitude: float | None
    gps_longitude: float | None
    diagnostics: tuple[ExtractionDiagnostic, ...]


_TIMESTAMP_FIELDS = ("CreateDate", "DateCreated", "ModifyDate")


def extract_xmp_metadata(media_path: Path) -> XmpMetadata:
    sidecar = _find_sidecar(media_path)
    if sidecar is None:
        return XmpMetadata(None, (), (), None, None, ())

    try:
        root = ElementTree.parse(sidecar).getroot()
    except (OSError, ElementTree.ParseError):
        return XmpMetadata(
            sidecar,
            (),
            (),
            None,
            None,
            (
                ExtractionDiagnostic(
                    source_kind="xmp",
                    diagnostic_type="unreadable",
                ),
            ),
        )

    values = _collect_values(root)
    candidates: list[TimestampCandidate] = []
    diagnostics: list[ExtractionDiagnostic] = []

    for field_name in _TIMESTAMP_FIELDS:
        raw_value = _first(values.get(field_name, ()))
        if raw_value is None:
            continue
        parsed = _parse_iso_timestamp(raw_value)
        if parsed is None:
            diagnostics.append(
                ExtractionDiagnostic(
                    source_kind="xmp",
                    diagnostic_type="invalid",
                    field_name=f"xmp_{field_name.lower()}",
                )
            )
            continue
        naive, offset = parsed
        candidates.append(
            TimestampCandidate(
                source_kind="xmp",
                source_detail=f"xmp_{field_name.lower()}",
                naive_timestamp=naive,
                precision="datetime",
                timezone_offset=offset,
            )
        )

    keywords = tuple(
        sorted(
            {
                value.strip()
            for field in ("subject", "hierarchicalSubject", "li")
                for value in values.get(field, ())
                if value.strip()
            },
            key=lambda value: (value.casefold(), value),
        )
    )

    latitude = _parse_coordinate(_first(values.get("GPSLatitude", ())), latitude=True)
    longitude = _parse_coordinate(
        _first(values.get("GPSLongitude", ())), latitude=False
    )
    if (latitude is None) != (longitude is None):
        diagnostics.append(
            ExtractionDiagnostic(
                source_kind="xmp",
                diagnostic_type="invalid",
                field_name="xmp_gps",
            )
        )
        latitude = None
        longitude = None

    return XmpMetadata(
        sidecar,
        tuple(candidates),
        keywords,
        latitude,
        longitude,
        tuple(diagnostics),
    )


def _find_sidecar(media_path: Path) -> Path | None:
    candidates = sorted(
        {media_path.with_suffix(".xmp"), media_path.with_suffix(".XMP")},
        key=lambda path: path.name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _collect_values(root: ElementTree.Element) -> dict[str, tuple[str, ...]]:
    collected: dict[str, list[str]] = {}
    for element in root.iter():
        local_name = _local_name(element.tag)
        if element.text and element.text.strip():
            collected.setdefault(local_name, []).append(element.text.strip())
        for key, value in element.attrib.items():
            if value.strip():
                collected.setdefault(_local_name(key), []).append(value.strip())
    return {key: tuple(value) for key, value in collected.items()}


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def _first(values: tuple[str, ...]) -> str | None:
    return values[0] if values else None


def _parse_iso_timestamp(value: str) -> tuple[datetime, timedelta | None] | None:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    offset = parsed.utcoffset()
    return parsed.replace(tzinfo=None), offset


def _parse_coordinate(value: str | None, *, latitude: bool) -> float | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    sign = 1.0
    if normalized.endswith(("S", "W")):
        sign = -1.0
        normalized = normalized[:-1]
    elif normalized.endswith(("N", "E")):
        normalized = normalized[:-1]
    try:
        result = sign * float(normalized)
    except ValueError:
        return None
    limit = 90 if latitude else 180
    if not -limit <= result <= limit:
        return None
    return result
