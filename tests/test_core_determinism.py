from __future__ import annotations

from datetime import datetime
from pathlib import Path

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


def test_scanner_skips_recognized_non_jpeg(tmp_path: Path) -> None:
    (tmp_path / "image.png").write_bytes(b"not a png")
    result = scan_directory(tmp_path)
    assert result.records == ()
    assert result.skipped[0].reason == "recognized_not_processable"
