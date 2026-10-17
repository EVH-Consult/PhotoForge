from dataclasses import replace
from datetime import datetime
from itertools import permutations
import json
from pathlib import Path

import pytest

from photoforge.metadata_extractors.filename import extract_filename_timestamp
from photoforge.model import FileRecord, MediaMetadata, TimestampCandidate
from photoforge.naming import NamingRules, load_naming_rules
from photoforge.planner import plan_files


def record(path, digest="a" * 64):
    return FileRecord(path, 10, datetime(2024, 2, 3, 4, 5, 6), "filesystem_mtime", digest, digest[:8])


def test_default_rules_preserve_existing_plan(tmp_path):
    source = record(tmp_path / "old.jpg")
    implicit = plan_files([source], output_path=tmp_path / "out")
    explicit = plan_files([source], output_path=tmp_path / "out", naming_rules=NamingRules())
    assert implicit == explicit
    assert implicit.actions[0].target_path == tmp_path / "out/2024/02/03/2024-02-03_040506_aaaaaaaa.jpg"


def test_camera_rules_sanitize_metadata_and_keep_provenance(tmp_path):
    source = record(tmp_path / "old.jpg")
    candidate = TimestampCandidate("filesystem", "mtime", source.timestamp, "datetime")
    source = replace(source, metadata=MediaMetadata((candidate,), candidate, camera_model="../../Camera: 1"))
    rules = NamingRules(filename="{camera_model}_{year}_{hash}", folder="{camera_make}/{camera_model}")
    result = plan_files([source], output_path=tmp_path / "out", naming_rules=rules)
    target = result.actions[0].target_path
    assert target.parent == tmp_path / "out/unknown/Camera_1"
    assert target.name == "Camera_1_2024_" + "a" * 64 + ".jpg"
    assert result.records[0].metadata == source.metadata
    assert result.records[0].timestamp_source == source.timestamp_source


def test_templates_collision_and_permutations(tmp_path):
    sources = [record(tmp_path / "a.jpg"), record(tmp_path / "b.jpg", "b" * 64)]
    rules = NamingRules(filename="same")
    expected = plan_files(sources, naming_rules=rules)
    assert [a.action for a in expected.actions] == ["rename", "collision"]
    for order in permutations(sources):
        assert plan_files(order, naming_rules=rules) == expected
    (tmp_path / "same.jpg").write_bytes(b"occupied")
    assert {a.action for a in plan_files(sources, naming_rules=rules).actions} == {"collision"}
    assert (tmp_path / "same.jpg").read_bytes() == b"occupied"


def test_group_folders_require_deliberate_opt_in(tmp_path):
    with pytest.raises(ValueError, match="requires use_context_groups"):
        NamingRules(folder="{event}")
    sources = [record(tmp_path / "a.jpg"), record(tmp_path / "b.jpg", "b" * 64)]
    rules = NamingRules(folder="{event}", use_context_groups=True)
    result = plan_files(sources, output_path=tmp_path / "out", naming_rules=rules)
    assert len({a.target_path.parent for a in result.actions}) == 1
    assert len(result.actions[0].target_path.parent.name) == 64
    assert result == plan_files(reversed(sources), output_path=tmp_path / "out", naming_rules=rules)
    with pytest.raises(ValueError, match="output directory"):
        plan_files(sources, naming_rules=rules)


def test_live_photo_uses_still_naming_and_collision_blocks_pair(tmp_path):
    still = replace(record(tmp_path / "a.heic"), media_format="heic", canonical_extension=".heic",
                    live_photo_pair_id="pair", live_photo_role="still")
    motion = replace(record(tmp_path / "a.mov", "b" * 64), timestamp=datetime(2025, 1, 1),
                     media_format="mov", canonical_extension=".mov", live_photo_pair_id="pair", live_photo_role="motion")
    rules = NamingRules(filename="{year}_event")
    result = plan_files([motion, still], naming_rules=rules)
    assert {a.target_path.name for a in result.actions} == {"2024_event.heic", "2024_event.mov"}
    (tmp_path / "2024_event.mov").write_bytes(b"occupied")
    assert {a.action for a in plan_files([still, motion], naming_rules=rules).actions} == {"collision"}


@pytest.mark.parametrize("template", ["../x", "/x", "a\\b", "{missing}", "{year.x}", "{year!r}", "{year:04}", "", "a//b"])
def test_invalid_template_rejected(template):
    with pytest.raises(ValueError):
        NamingRules(filename=template)


@pytest.mark.parametrize("template", ["CON", "..", "name.", "name ", "x" * 121])
def test_unsafe_rendered_component_rejected(tmp_path, template):
    with pytest.raises(ValueError):
        plan_files([record(tmp_path / "old.jpg")], naming_rules=NamingRules(filename=template))


@pytest.mark.parametrize("data", [{"version": True}, {"version": 2}, {"version": 1, "typo": 1},
                                   {"version": 1, "use_context_groups": "yes"}, []])
def test_invalid_config_rejected(tmp_path, data):
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_naming_rules(path)


def test_config_defaults_and_explicit_precedence(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text('{"version":1,"filename":"{year}"}', encoding="utf-8")
    assert load_naming_rules(path) == NamingRules(filename="{year}")


@pytest.mark.parametrize("filename,detail", [
    ("IMG_20240203040506.jpg", "filename_yyyymmddhhmmss"),
    ("IMG_2024-02-03T04-05-06.jpg", "filename_yyyy-mm-ddT_hh-mm-ss"),
])
def test_additional_filename_datetime_patterns(filename, detail):
    candidate, = extract_filename_timestamp(filename)
    assert candidate.naive_timestamp == datetime(2024, 2, 3, 4, 5, 6)
    assert candidate.source_detail == detail
    assert candidate.timezone_offset is None
