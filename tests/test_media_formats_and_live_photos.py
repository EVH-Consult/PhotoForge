from __future__ import annotations

from pathlib import Path

from PIL import Image

from photoforge.planner import plan_files
from photoforge.scanner import scan_directory


def _write_ftyp(path: Path, brand: bytes) -> None:
    path.write_bytes((16).to_bytes(4, "big") + b"ftyp" + brand + b"\x00\x00\x00\x00")


def _write_tiff_header(path: Path) -> None:
    path.write_bytes(b"II*\x00\x08\x00\x00\x00")


def test_all_introduced_formats_are_processed_with_normalized_extensions(
    tmp_path: Path,
) -> None:
    Image.new("RGB", (1, 1)).save(tmp_path / "png_20240102_030405.png")
    Image.new("RGB", (1, 1)).save(tmp_path / "tiff_20240102_030405.tiff")
    _write_ftyp(tmp_path / "heic_20240102_030405.heic", b"heic")
    _write_ftyp(tmp_path / "heif_20240102_030405.heif", b"mif1")
    (tmp_path / "cr2_20240102_030405.cr2").write_bytes(
        b"II*\x00\x08\x00\x00\x00CR\x02\x00"
    )
    _write_tiff_header(tmp_path / "nef_20240102_030405.nef")
    with (tmp_path / "nef_20240102_030405.nef").open("ab") as stream:
        stream.write(b"nef")
    _write_tiff_header(tmp_path / "arw_20240102_030405.arw")
    with (tmp_path / "arw_20240102_030405.arw").open("ab") as stream:
        stream.write(b"arw")
    _write_ftyp(tmp_path / "mp4_20240102_030405.mp4", b"isom")
    _write_ftyp(tmp_path / "mov_20240102_030405.mov", b"qt  ")

    result = scan_directory(tmp_path)

    assert result.skipped == ()
    assert result.issues == ()
    assert result.supported_files_processed == 9
    assert {record.media_format for record in result.records} == {
        "png",
        "tiff",
        "heic",
        "heif",
        "cr2",
        "nef",
        "arw",
        "mp4",
        "mov",
    }

    planned = plan_files(result.records)
    suffixes = {
        record.path.suffix: Path(record.canonical_filename).suffix
        for record in planned.records
    }
    assert suffixes == {
        ".png": ".png",
        ".tiff": ".tif",
        ".heic": ".heic",
        ".heif": ".heif",
        ".cr2": ".cr2",
        ".nef": ".nef",
        ".arw": ".arw",
        ".mp4": ".mp4",
        ".mov": ".mov",
    }


def test_live_photo_pair_uses_one_logical_asset_and_shared_basename(
    tmp_path: Path,
) -> None:
    _write_ftyp(tmp_path / "IMG_20240102_030405.heic", b"heic")
    _write_ftyp(tmp_path / "IMG_20240102_030405.mov", b"qt  ")

    result = scan_directory(tmp_path)

    assert len(result.records) == 2
    assert len({record.live_photo_pair_id for record in result.records}) == 1
    assert None not in {record.live_photo_pair_id for record in result.records}
    assert {record.live_photo_role for record in result.records} == {"still", "motion"}

    planned = plan_files(result.records)
    assert len({record.duplicate_group_id for record in planned.records}) == 1
    assert all(record.canonical for record in planned.records)
    assert all(record.duplicate_group_size == 1 for record in planned.records)
    bases = {Path(record.canonical_filename).stem for record in planned.records}
    assert len(bases) == 1
    assert {Path(record.canonical_filename).suffix for record in planned.records} == {
        ".heic",
        ".mov",
    }


def test_duplicate_live_photos_are_deduplicated_as_complete_assets(
    tmp_path: Path,
) -> None:
    for folder_name in ("a", "b"):
        folder = tmp_path / folder_name
        folder.mkdir()
        _write_ftyp(folder / "IMG_20240102_030405.heic", b"heic")
        _write_ftyp(folder / "IMG_20240102_030405.mov", b"qt  ")

    planned = plan_files(scan_directory(tmp_path).records)

    assert len({record.duplicate_group_id for record in planned.records}) == 1
    assert sum(record.canonical for record in planned.records) == 2
    assert sum(not record.canonical for record in planned.records) == 2
    assert all(record.duplicate_group_size == 2 for record in planned.records)


def test_live_photo_collision_blocks_both_components(tmp_path: Path) -> None:
    _write_ftyp(tmp_path / "IMG_20240102_030405.heic", b"heic")
    _write_ftyp(tmp_path / "IMG_20240102_030405.mov", b"qt  ")
    records = scan_directory(tmp_path).records
    initial = plan_files(records)
    target = next(
        record.target_path
        for record in initial.records
        if record.live_photo_role == "motion"
    )
    assert target is not None
    target.write_bytes(b"occupied")

    planned = plan_files(records)

    assert {record.action_status for record in planned.records} == {"collision"}
    assert {action.action for action in planned.actions} == {"collision"}


def test_ambiguous_live_photo_candidates_remain_independent(tmp_path: Path) -> None:
    Image.new("RGB", (1, 1)).save(tmp_path / "IMG_20240102_030405.jpg")
    _write_ftyp(tmp_path / "IMG_20240102_030405.heic", b"heic")
    _write_ftyp(tmp_path / "IMG_20240102_030405.mov", b"qt  ")

    result = scan_directory(tmp_path)

    assert all(record.live_photo_pair_id is None for record in result.records)
    assert [issue.code for issue in result.issues] == [
        "ambiguous_live_photo_pair",
        "ambiguous_live_photo_pair",
        "ambiguous_live_photo_pair",
    ]


def test_invalid_new_format_is_corrupt_but_invalid_jpeg_keeps_legacy_fallback(
    tmp_path: Path,
) -> None:
    (tmp_path / "bad_20240102_030405.png").write_bytes(b"not-png")
    (tmp_path / "legacy_20240102_030405.jpg").write_bytes(b"not-jpeg")

    result = scan_directory(tmp_path)

    assert [record.path.name for record in result.records] == [
        "legacy_20240102_030405.jpg"
    ]
    assert [(item.path.name, item.reason) for item in result.skipped] == [
        ("bad_20240102_030405.png", "corrupt_metadata_unreadable")
    ]
