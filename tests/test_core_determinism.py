from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

from photoforge.grouping import build_contextual_grouping
from photoforge.model import ContextualGrouping, FileRecord, PlanResult
from photoforge.pipeline import run_pipeline
from photoforge.planner import plan_files
from photoforge.scanner import ScanResult, scan_directory


def _record(path: Path, sha: str, source: str = "filesystem_mtime") -> FileRecord:
    return FileRecord(path, 10, datetime(2024, 1, 2, 3, 4, 5), source, sha, sha[:8])


def test_contextual_ids_do_not_depend_on_input_root() -> None:
    first = build_contextual_grouping((_record(Path("C:/one/a.jpg"), "a" * 64),))
    second = build_contextual_grouping((_record(Path("D:/two/a.jpg"), "a" * 64),))
    assert first == second
    assert first.groups[0].member_refs == ("a.jpg",)


def test_canonical_selection_prefers_actual_exif_source() -> None:
    records = (
        _record(Path("a.jpg"), "a" * 64),
        _record(Path("z.jpg"), "a" * 64, "exif_datetimeoriginal"),
    )
    result = plan_files(records)
    assert next(item for item in result.records if item.canonical).path == Path("z.jpg")


def test_planner_reserves_targets_within_one_plan(tmp_path: Path) -> None:
    records = (
        _record(tmp_path / "a.jpg", "12345678" + "a" * 56),
        _record(tmp_path / "b.jpg", "12345678" + "b" * 56),
    )
    result = plan_files(records)
    assert tuple(action.action for action in result.actions) == ("rename", "collision")


def test_pipeline_reuses_supplied_scan_result(monkeypatch, tmp_path: Path) -> None:
    scan_result = ScanResult((), (), (), 0, 0)
    monkeypatch.setattr(
        "photoforge.pipeline.scan_directory",
        lambda _: (_ for _ in ()).throw(AssertionError("unexpected second scan")),
    )
    result, grouping = run_pipeline(tmp_path, scan_result=scan_result)
    assert result == PlanResult((), (), ())
    assert grouping == ContextualGrouping(())


def test_scanner_rejects_corrupt_newly_supported_format(tmp_path: Path) -> None:
    (tmp_path / "image.png").write_bytes(b"not a png")
    result = scan_directory(tmp_path)
    assert result.records == ()
    assert result.skipped[0].reason == "corrupt_metadata_unreadable"


def test_scanner_integrates_filename_fallback_and_structured_metadata(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "IMG_20240102_030405.jpg"
    Image.new("RGB", (1, 1)).save(image_path)

    result = scan_directory(tmp_path)

    assert len(result.records) == 1
    record = result.records[0]
    assert record.timestamp == datetime(2024, 1, 2, 3, 4, 5)
    assert record.timestamp_source == "filename_yyyymmdd_hhmmss"
    assert record.metadata is not None
    assert tuple(
        candidate.source_kind for candidate in record.metadata.timestamp_candidates
    ) == ("filename", "filesystem")
    assert result.batch_contexts[0].classification == "insufficient_evidence"


def test_scanner_infers_unanimous_trusted_device_offset(tmp_path: Path) -> None:
    first_exif = Image.Exif()
    first_exif[271] = "Example"
    first_exif[272] = "Camera"
    first_exif[36867] = "2024:01:02 12:00:00"
    first_exif[36881] = "+02:00"
    Image.new("RGB", (1, 1)).save(tmp_path / "a.jpg", exif=first_exif)

    second_exif = Image.Exif()
    second_exif[271] = "Example"
    second_exif[272] = "Camera"
    second_exif[36867] = "2024:01:02 13:00:00"
    Image.new("RGB", (1, 1)).save(tmp_path / "b.jpg", exif=second_exif)

    result = scan_directory(tmp_path)
    second = next(record for record in result.records if record.path.name == "b.jpg")

    assert second.timestamp == datetime(2024, 1, 2, 11, 0, 0)
    assert second.metadata is not None
    assert second.metadata.timezone_basis == "trusted_device_cluster"
    assert second.metadata.selected_candidate.timezone_offset == timedelta(hours=2)
    assert result.batch_contexts[0].classification == "event_bounded"
