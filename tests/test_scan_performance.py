import os
import time

import pytest
from PIL import Image

from photoforge.hashing import ordered_hashes
from photoforge.pipeline import run_pipeline
from photoforge.reporter import render_json_report
from photoforge.scanner import scan_directory


def test_parallel_scan_matches_serial_complete_models_and_reports(tmp_path):
    for i in range(16):
        Image.new("RGB", (2, 2), (i, 0, 0)).save(tmp_path / f"IMG_20240102_030405_{i}.jpg")
    (tmp_path / "bad.png").write_bytes(b"corrupt")
    (tmp_path / "ignored.txt").write_text("synthetic", encoding="utf-8")
    serial = scan_directory(tmp_path)
    parallel = scan_directory(tmp_path, hash_workers=4)
    assert serial == parallel
    first, groups = run_pipeline(tmp_path, scan_result=serial)
    second, other_groups = run_pipeline(tmp_path, scan_result=parallel)
    assert (first, groups) == (second, other_groups)
    assert render_json_report(first) == render_json_report(second)


def test_completion_order_and_errors_cannot_reorder_hashes():
    def hash_function(path):
        time.sleep((5 - path) * .001)
        if path == 2:
            raise OSError("controlled failure")
        return str(path)
    results = list(ordered_hashes(range(6), 3, hash_function=hash_function))
    assert [str(r) for r in results] == ["0", "1", "controlled failure", "3", "4", "5"]
    assert isinstance(results[2], OSError)


def test_queued_work_is_bounded():
    consumed = []
    def paths():
        for i in range(100):
            consumed.append(i)
            yield i
    hashes = ordered_hashes(paths(), 2, hash_function=str)
    assert next(hashes) == "0"
    assert len(consumed) == 4
    hashes.close()


def test_same_size_restored_mtime_and_sidecar_change_are_rescanned(tmp_path):
    path = tmp_path / "IMG_20240102_030405.jpg"
    path.write_bytes(b"aaaa")
    old_stat = path.stat()
    first = scan_directory(tmp_path, hash_workers=2)
    path.write_bytes(b"bbbb")
    os.utime(path, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    second = scan_directory(tmp_path, hash_workers=2)
    assert first.records[0].sha256 != second.records[0].sha256
    sidecar = path.with_suffix(".xmp")
    sidecar.write_text('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmp:CreateDate="2025-01-01T12:00:00Z"/></rdf:RDF></x:xmpmeta>', encoding="utf-8")
    third = scan_directory(tmp_path, hash_workers=2)
    assert third.records[0].timestamp != second.records[0].timestamp


@pytest.mark.parametrize("workers", [0, 33, -1, True, 1.5])
def test_invalid_worker_count(workers, tmp_path):
    with pytest.raises(ValueError, match="hash_workers"):
        scan_directory(tmp_path, hash_workers=workers)
