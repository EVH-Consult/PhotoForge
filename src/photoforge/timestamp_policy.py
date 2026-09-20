from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Any

from .model import TimestampCandidate


@dataclass(frozen=True)
class CorrectionRule:
    timezone_offset: timedelta | None = None
    clock_correction: timedelta | None = None


@dataclass(frozen=True)
class FolderRule:
    path: str
    correction: CorrectionRule


@dataclass(frozen=True)
class DeviceRule:
    make: str
    model: str
    correction: CorrectionRule


@dataclass(frozen=True)
class GpsRule:
    name: str
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float
    timezone_offset: timedelta

    def contains(self, latitude: float, longitude: float) -> bool:
        return (
            self.min_latitude <= latitude <= self.max_latitude
            and self.min_longitude <= longitude <= self.max_longitude
        )


@dataclass(frozen=True)
class TimestampPolicy:
    default: CorrectionRule = CorrectionRule()
    folder_rules: tuple[FolderRule, ...] = ()
    device_rules: tuple[DeviceRule, ...] = ()
    gps_rules: tuple[GpsRule, ...] = ()


@dataclass(frozen=True)
class PolicyContext:
    relative_folder: str
    camera_make: str | None
    camera_model: str | None
    gps_latitude: float | None
    gps_longitude: float | None
    trusted_device_offset: timedelta | None = None


@dataclass(frozen=True)
class AppliedTimestampPolicy:
    candidate: TimestampCandidate
    timezone_basis: str | None
    clock_correction: timedelta | None


def load_timestamp_policy(path: Path) -> TimestampPolicy:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read timestamp policy: {path}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("timestamp policy must be an object with version 1")

    default = _parse_correction(data.get("default", {}), "default")
    folder_rules = tuple(
        FolderRule(
            path=_require_relative_path(item.get("path"), "folder rule path"),
            correction=_parse_correction(item, "folder rule"),
        )
        for item in _object_list(data.get("folder_rules", []), "folder_rules")
    )
    device_rules = tuple(
        DeviceRule(
            make=_require_text(item.get("make"), "device rule make"),
            model=_require_text(item.get("model"), "device rule model"),
            correction=_parse_correction(item, "device rule"),
        )
        for item in _object_list(data.get("device_rules", []), "device_rules")
    )
    gps_rules = tuple(
        _parse_gps_rule(item)
        for item in _object_list(data.get("gps_rules", []), "gps_rules")
    )

    _require_unique((rule.path for rule in folder_rules), "folder rule path")
    _require_unique(
        (f"{rule.make}\0{rule.model}" for rule in device_rules),
        "device rule make/model",
    )
    _require_unique((rule.name for rule in gps_rules), "GPS rule name")
    return TimestampPolicy(default, folder_rules, device_rules, gps_rules)


def apply_timestamp_policy(
    candidate: TimestampCandidate,
    policy: TimestampPolicy,
    context: PolicyContext,
) -> AppliedTimestampPolicy:
    # Filesystem mtime is extracted as UTC. Camera-local correction and timezone
    # inference rules must never reinterpret that already-normalized fallback.
    if candidate.source_kind == "filesystem":
        return AppliedTimestampPolicy(candidate, "filesystem_utc", None)

    explicit_rule, explicit_basis = _select_explicit_rule(policy, context)

    correction = explicit_rule.clock_correction
    corrected = candidate
    if correction is not None:
        corrected = replace(
            candidate,
            naive_timestamp=candidate.naive_timestamp + correction,
        )
    else:
        correction = None

    timezone_offset = explicit_rule.timezone_offset
    timezone_basis = explicit_basis if timezone_offset is not None else None
    if timezone_offset is None and corrected.timezone_offset is not None:
        timezone_offset = corrected.timezone_offset
        timezone_basis = "embedded"
    if timezone_offset is None:
        gps_offset, gps_basis = _gps_offset(policy, context)
        if gps_offset is not None:
            timezone_offset = gps_offset
            timezone_basis = gps_basis
    if timezone_offset is None and context.trusted_device_offset is not None:
        timezone_offset = context.trusted_device_offset
        timezone_basis = "trusted_device_cluster"
    if timezone_offset is None and policy.default.timezone_offset is not None:
        timezone_offset = policy.default.timezone_offset
        timezone_basis = "default"

    if timezone_offset != corrected.timezone_offset:
        corrected = replace(corrected, timezone_offset=timezone_offset)

    return AppliedTimestampPolicy(corrected, timezone_basis, correction)


def _select_explicit_rule(
    policy: TimestampPolicy,
    context: PolicyContext,
) -> tuple[CorrectionRule, str | None]:
    for rule in policy.folder_rules:
        if rule.path == context.relative_folder:
            return rule.correction, f"folder:{rule.path}"
    if context.camera_make is not None and context.camera_model is not None:
        for rule in policy.device_rules:
            if rule.make == context.camera_make and rule.model == context.camera_model:
                return rule.correction, f"device:{rule.make}/{rule.model}"
    return CorrectionRule(clock_correction=policy.default.clock_correction), "default"


def _gps_offset(
    policy: TimestampPolicy,
    context: PolicyContext,
) -> tuple[timedelta | None, str | None]:
    if context.gps_latitude is None or context.gps_longitude is None:
        return None, None
    matches = tuple(
        rule
        for rule in policy.gps_rules
        if rule.contains(context.gps_latitude, context.gps_longitude)
    )
    if not matches:
        return None, None
    offsets = {rule.timezone_offset for rule in matches}
    if len(offsets) != 1:
        raise ValueError("GPS matches multiple rules with different timezone offsets")
    return matches[0].timezone_offset, f"gps:{matches[0].name}"


def _parse_correction(value: Any, label: str) -> CorrectionRule:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return CorrectionRule(
        timezone_offset=_parse_optional_offset(value.get("timezone_offset"), label),
        clock_correction=_parse_optional_offset(value.get("clock_correction"), label),
    )


def _parse_gps_rule(value: dict[str, Any]) -> GpsRule:
    name = _require_text(value.get("name"), "GPS rule name")
    bounds = value.get("bounds")
    if not isinstance(bounds, list) or len(bounds) != 4:
        raise ValueError(f"GPS rule {name!r} bounds must contain four numbers")
    if not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in bounds):
        raise ValueError(f"GPS rule {name!r} bounds must contain four numbers")
    min_latitude, max_latitude, min_longitude, max_longitude = map(float, bounds)
    if not -90 <= min_latitude <= max_latitude <= 90:
        raise ValueError(f"GPS rule {name!r} latitude bounds are invalid")
    if not -180 <= min_longitude <= max_longitude <= 180:
        raise ValueError(f"GPS rule {name!r} longitude bounds are invalid")
    offset = _parse_optional_offset(value.get("timezone_offset"), f"GPS rule {name!r}")
    if offset is None:
        raise ValueError(f"GPS rule {name!r} requires timezone_offset")
    return GpsRule(
        name,
        min_latitude,
        max_latitude,
        min_longitude,
        max_longitude,
        offset,
    )


def _parse_optional_offset(value: Any, label: str) -> timedelta | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != 6 or value[0] not in "+-" or value[3] != ":":
        raise ValueError(f"{label} offset must use +HH:MM or -HH:MM")
    if not value[1:3].isdigit() or not value[4:6].isdigit():
        raise ValueError(f"{label} offset must use +HH:MM or -HH:MM")
    hours = int(value[1:3])
    minutes = int(value[4:6])
    if hours > 23 or minutes > 59:
        raise ValueError(f"{label} offset is outside the supported range")
    result = timedelta(hours=hours, minutes=minutes)
    return -result if value[0] == "-" else result


def _object_list(value: Any, label: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be a list of objects")
    return tuple(value)


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _require_relative_path(value: Any, label: str) -> str:
    text = _require_text(value, label).replace("\\", "/").strip("/")
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a safe relative path")
    return path.as_posix()


def _require_unique(values: Any, label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {label}: {value}")
        seen.add(value)
