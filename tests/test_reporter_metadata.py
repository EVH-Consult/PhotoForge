from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from photoforge.model import MediaMetadata, PlanResult, PlannedRecord, TimestampCandidate
from photoforge.reporter import render_json_report


def test_json_report_exposes_structured_timestamp_representations() -> None:
    candidate = TimestampCandidate(
        source_kind="exif",
        source_detail="exif_datetimeoriginal",
        naive_timestamp=datetime(2024, 1, 2, 12, 0, 0),
        precision="datetime",
        timezone_offset=timedelta(hours=2),
    )
    metadata = MediaMetadata(
        timestamp_candidates=(candidate,),
        selected_candidate=candidate,
        timezone_basis="embedded",
    )
    record = PlannedRecord(
        path=Path("photo.jpg"),
        duplicate_group_id="a" * 64,
        duplicate_group_size=1,
        canonical=True,
        canonical_filename="2024-01-02_100000_aaaaaaaa.jpg",
        target_path=Path("2024-01-02_100000_aaaaaaaa.jpg"),
        action_status="rename",
        sha256="a" * 64,
        short_hash="aaaaaaaa",
        timestamp=datetime(2024, 1, 2, 10, 0, 0),
        timestamp_source="exif_datetimeoriginal",
        metadata=metadata,
    )

    payload = json.loads(render_json_report(PlanResult((record,), (), ())))
    structured = payload["records"][0]["metadata"]["selected_candidate"]

    assert structured["naive_timestamp"] == "2024-01-02 12:00:00"
    assert structured["aware_timestamp"] == "2024-01-02T12:00:00+02:00"
    assert structured["utc_timestamp"] == "2024-01-02T10:00:00+00:00"
    assert structured["timezone_offset"] == "+02:00"
