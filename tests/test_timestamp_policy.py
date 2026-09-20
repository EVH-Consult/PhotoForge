from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from photoforge.model import TimestampCandidate
from photoforge.timestamp_policy import (
    PolicyContext,
    apply_timestamp_policy,
    load_timestamp_policy,
)


def _candidate(offset: timedelta | None = None) -> TimestampCandidate:
    return TimestampCandidate(
        source_kind="exif",
        source_detail="exif_datetimeoriginal",
        naive_timestamp=datetime(2024, 1, 2, 12, 0, 0),
        precision="datetime",
        timezone_offset=offset,
    )


def _load(tmp_path: Path, payload: dict[str, object]):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_timestamp_policy(path)


def test_folder_rule_applies_clock_correction_and_timezone(tmp_path: Path) -> None:
    policy = _load(
        tmp_path,
        {
            "version": 1,
            "folder_rules": [
                {
                    "path": "trip/day-1",
                    "clock_correction": "-01:00",
                    "timezone_offset": "+02:00",
                }
            ],
        },
    )
    context = PolicyContext("trip/day-1", "Canon", "X", None, None)

    result = apply_timestamp_policy(_candidate(), policy, context)

    assert result.candidate.naive_timestamp == datetime(2024, 1, 2, 11, 0, 0)
    assert result.candidate.timezone_offset == timedelta(hours=2)
    assert result.timezone_basis == "folder:trip/day-1"
    assert result.clock_correction == timedelta(hours=-1)


def test_embedded_offset_precedes_gps_and_default_rules(tmp_path: Path) -> None:
    policy = _load(
        tmp_path,
        {
            "version": 1,
            "default": {"timezone_offset": "+01:00"},
            "gps_rules": [
                {
                    "name": "region",
                    "bounds": [49.0, 52.0, 2.0, 7.0],
                    "timezone_offset": "+02:00",
                }
            ],
        },
    )
    context = PolicyContext("", None, None, 50.8, 4.3)

    result = apply_timestamp_policy(_candidate(timedelta(hours=3)), policy, context)

    assert result.candidate.timezone_offset == timedelta(hours=3)
    assert result.timezone_basis == "embedded"


def test_gps_rule_is_used_before_trusted_device_and_default(tmp_path: Path) -> None:
    policy = _load(
        tmp_path,
        {
            "version": 1,
            "default": {"timezone_offset": "+01:00"},
            "gps_rules": [
                {
                    "name": "belgium",
                    "bounds": [49.0, 52.0, 2.0, 7.0],
                    "timezone_offset": "+02:00",
                }
            ],
        },
    )
    context = PolicyContext(
        "",
        "Canon",
        "X",
        50.8,
        4.3,
        trusted_device_offset=timedelta(hours=3),
    )

    result = apply_timestamp_policy(_candidate(), policy, context)

    assert result.candidate.timezone_offset == timedelta(hours=2)
    assert result.timezone_basis == "gps:belgium"


def test_policy_does_not_reinterpret_filesystem_mtime(tmp_path: Path) -> None:
    policy = _load(
        tmp_path,
        {
            "version": 1,
            "default": {
                "clock_correction": "-01:00",
                "timezone_offset": "+02:00",
            },
            "folder_rules": [
                {
                    "path": "trip/day-1",
                    "clock_correction": "+03:00",
                    "timezone_offset": "+04:00",
                }
            ],
        },
    )
    candidate = TimestampCandidate(
        source_kind="filesystem",
        source_detail="filesystem_mtime",
        naive_timestamp=datetime(2024, 1, 2, 12, 0, 0),
        precision="datetime",
        timezone_offset=timedelta(0),
    )
    context = PolicyContext("trip/day-1", "Canon", "X", 50.8, 4.3)

    result = apply_timestamp_policy(candidate, policy, context)

    assert result.candidate == candidate
    assert result.timezone_basis == "filesystem_utc"
    assert result.clock_correction is None
