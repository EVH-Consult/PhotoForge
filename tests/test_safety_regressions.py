"""Contract regressions using only synthetic files and controlled failures."""
from datetime import datetime, timedelta
from itertools import permutations
from pathlib import Path

import pytest
from PIL import Image

from photoforge import cli, scanner
from photoforge.grouping import build_contextual_grouping
from photoforge.hashing import CHUNK_SIZE, compute_sha256
from photoforge.model import FileRecord
from photoforge.planner import plan_files


def record(path, digest="a" * 64, size=10, source="filesystem_mtime", seconds=0):
    return FileRecord(path, size, datetime(2024, 1, 2) + timedelta(seconds=seconds),
                      source, digest, digest[:8])


@pytest.mark.parametrize("size", [0, CHUNK_SIZE - 1, CHUNK_SIZE, CHUNK_SIZE + 1])
def test_full_hash_crosses_chunk_boundary(tmp_path, size):
    import hashlib
    data = b"x" * size
    path = tmp_path / "synthetic.bin"
    path.write_bytes(data)
    assert compute_sha256(path) == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("failure,reason", [
    (OSError("controlled unreadable file"), "corrupt_file_unreadable"),
    (RuntimeError("controlled hash failure"), "corrupt_hash_failed"),
])
def test_hash_failure_is_corrupt_and_never_planned(tmp_path, monkeypatch, failure, reason):
    path = tmp_path / "IMG_20240102_030405.jpg"
    Image.new("RGB", (1, 1)).save(path)
    def fail(_):
        raise failure
    monkeypatch.setattr(scanner, "compute_sha256", fail)
    result = scanner.scan_directory(tmp_path)
    assert result.records == ()
    assert [(s.path, s.reason) for s in result.skipped] == [(path, reason)]
    assert [i.code for i in result.issues] == [reason]
    assert plan_files(result.records).actions == ()


def test_canonical_size_then_exif_then_path_is_permutation_invariant(tmp_path):
    records = [record(tmp_path / "a.jpg", size=9, source="exif_datetimeoriginal"),
               record(tmp_path / "b.jpg"), record(tmp_path / "c.jpg")]
    expected = plan_files(records)
    assert next(r.path for r in expected.records if r.canonical) == tmp_path / "b.jpg"
    for order in permutations(records):
        assert plan_files(order) == expected


def test_existing_target_is_preserved_and_duplicate_has_no_action(tmp_path):
    records = [record(tmp_path / "a.jpg"), record(tmp_path / "b.jpg")]
    first = plan_files(records)
    target = first.actions[0].target_path
    target.write_bytes(b"existing content")
    second = plan_files(records)
    assert [a.action for a in second.actions] == ["collision"]
    assert [(r.action_status, r.target_path) for r in second.records if not r.canonical] == [("duplicate", None)]
    assert target.read_bytes() == b"existing content"


def test_context_window_inclusive_boundary_and_transitive_chain(tmp_path):
    records = tuple(record(tmp_path / f"{n}.jpg", seconds=s)
                    for n, s in enumerate((0, 300, 600, 901)))
    expected = build_contextual_grouping(records)
    assert sorted(len(g.member_refs) for g in expected.groups) == [1, 3]
    assert build_contextual_grouping(tuple(reversed(records))) == expected


def test_default_cli_is_read_only_and_context_does_not_change_plan(tmp_path, monkeypatch, capsys):
    path = tmp_path / "IMG_20240102_030405.jpg"
    Image.new("RGB", (1, 1)).save(path)
    original = path.read_bytes()
    def unexpected(_):
        raise AssertionError("dry-run attempted mutation")
    monkeypatch.setattr(cli, "apply_actions", unexpected)
    assert cli.main([str(tmp_path), "--json"]) == 0
    import json
    plain = json.loads(capsys.readouterr().out)
    assert cli.main([str(tmp_path), "--json", "--context"]) == 0
    contextual = json.loads(capsys.readouterr().out)
    contextual.pop("contextual_groups", None)
    assert contextual == plain
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_invalid_input_rejected_before_scan(tmp_path, monkeypatch, kind):
    path = tmp_path / kind
    if kind == "file":
        path.write_text("synthetic", encoding="utf-8")
    monkeypatch.setattr(cli, "scan_directory", lambda *a, **k: pytest.fail("unexpected scan"))
    with pytest.raises(ValueError, match="Input path"):
        cli.main([str(path)])
