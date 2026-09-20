# src/photoforge/metadata_extractors/exif.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from ..model import ExtractionDiagnostic, TimestampCandidate

_EXIF_DATETIME_TAGS: tuple[tuple[int, str, int], ...] = (
    (36867, "exif_datetimeoriginal", 36881),
    (36868, "exif_datetimedigitized", 36882),
    (306, "exif_datetime", 36880),
)

_EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"


@dataclass(frozen=True)
class ExifContext:
    camera_make: str | None
    camera_model: str | None
    keywords: tuple[str, ...]
    gps_latitude: float | None
    gps_longitude: float | None


def extract_exif_context(path: Path) -> ExifContext:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            make = _clean_text(exif.get(271))
            model = _clean_text(exif.get(272))
            keywords = _parse_keywords(exif.get(40094))
            gps = exif.get_ifd(34853) if 34853 in exif else {}
    except (OSError, UnidentifiedImageError, KeyError, TypeError, ValueError):
        return ExifContext(None, None, (), None, None)

    latitude = _parse_gps_coordinate(gps.get(2), gps.get(1), latitude=True)
    longitude = _parse_gps_coordinate(gps.get(4), gps.get(3), latitude=False)
    if (latitude is None) != (longitude is None):
        latitude = None
        longitude = None
    return ExifContext(make, model, keywords, latitude, longitude)


def extract_exif_timestamp_candidates(path: Path) -> tuple[TimestampCandidate, ...]:
    candidates, _ = extract_exif_metadata(path)
    return candidates


def extract_exif_diagnostics(path: Path) -> tuple[ExtractionDiagnostic, ...]:
    _, diagnostics = extract_exif_metadata(path)
    return diagnostics


def extract_exif_metadata(
    path: Path,
) -> tuple[tuple[TimestampCandidate, ...], tuple[ExtractionDiagnostic, ...]]:
    status, exif = _load_exif(path)

    if status == "missing":
        return (), (ExtractionDiagnostic(source_kind="exif", diagnostic_type="missing"),)

    if status == "unreadable":
        return (), (ExtractionDiagnostic(source_kind="exif", diagnostic_type="unreadable"),)

    candidates: list[TimestampCandidate] = []
    diagnostics: list[ExtractionDiagnostic] = []

    for timestamp_tag_id, source_detail, timezone_tag_id in _EXIF_DATETIME_TAGS:
        timestamp_value = exif.get(timestamp_tag_id)

        if timestamp_value is None:
            continue

        parsed_timestamp = _parse_exif_datetime(timestamp_value)
        if parsed_timestamp is None:
            diagnostics.append(
                ExtractionDiagnostic(
                    source_kind="exif",
                    diagnostic_type="invalid",
                    field_name=source_detail,
                )
            )
            continue

        timezone_value = exif.get(timezone_tag_id)
        parsed_timezone_offset = _parse_exif_offset(timezone_value)

        if timezone_value is not None and parsed_timezone_offset is None:
            diagnostics.append(
                ExtractionDiagnostic(
                    source_kind="exif",
                    diagnostic_type="invalid",
                    field_name=f"{source_detail}_offset",
                )
            )

        candidates.append(
            TimestampCandidate(
                source_kind="exif",
                source_detail=source_detail,
                naive_timestamp=parsed_timestamp,
                precision="datetime",
                timezone_offset=parsed_timezone_offset,
            )
        )

    if not candidates and not diagnostics:
        diagnostics.append(
            ExtractionDiagnostic(
                source_kind="exif",
                diagnostic_type="missing",
            )
        )


    return tuple(candidates), tuple(diagnostics)


def _load_exif(path: Path) -> tuple[str, dict[int, object]]:
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            if not exif:
                return "missing", {}
            return "ok", dict(exif)
    except (OSError, UnidentifiedImageError):
        return "unreadable", {}


def _parse_exif_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None

    try:
        return datetime.strptime(value, _EXIF_DATETIME_FORMAT)
    except ValueError:
        return None


def _parse_exif_offset(value: object) -> timedelta | None:
    if not isinstance(value, str):
        return None

    if len(value) != 6:
        return None

    sign = value[0]
    if sign not in {"+", "-"}:
        return None

    if value[3] != ":":
        return None

    hour_text = value[1:3]
    minute_text = value[4:6]

    if not hour_text.isdigit() or not minute_text.isdigit():
        return None

    hours = int(hour_text)
    minutes = int(minute_text)

    if hours > 23 or minutes > 59:
        return None

    offset = timedelta(hours=hours, minutes=minutes)
    if sign == "-":
        offset = -offset

    return offset


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().strip("\x00")
    return cleaned or None


def _parse_keywords(value: object) -> tuple[str, ...]:
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-16-le").strip("\x00")
        except UnicodeDecodeError:
            return ()
    elif isinstance(value, str):
        text = value
    else:
        return ()
    return tuple(
        sorted(
            {item.strip() for item in text.replace(",", ";").split(";") if item.strip()},
            key=lambda item: (item.casefold(), item),
        )
    )


def _parse_gps_coordinate(
    values: object,
    reference: object,
    *,
    latitude: bool,
) -> float | None:
    if not isinstance(values, (tuple, list)) or len(values) != 3:
        return None
    if not isinstance(reference, str):
        return None
    try:
        degrees, minutes, seconds = (float(value) for value in values)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    result = degrees + minutes / 60 + seconds / 3600
    if reference.upper() in {"S", "W"}:
        result = -result
    elif reference.upper() not in {"N", "E"}:
        return None
    limit = 90 if latitude else 180
    if not -limit <= result <= limit:
        return None
    return result
