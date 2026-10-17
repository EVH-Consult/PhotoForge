"""Synthetic, read-only scan comparison. No timing thresholds or external data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from photoforge.pipeline import run_pipeline
from photoforge.reporter import render_json_report
from photoforge.scanner import scan_directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--small-count", type=int, default=2000)
    parser.add_argument("--large-count", type=int, default=32)
    parser.add_argument("--large-mib", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if min(args.small_count, args.large_count, args.large_mib, args.repeats) < 1:
        parser.error("all counts and sizes must be positive")
    results = []
    for name, count, size in [("many-small", args.small_count, 4096),
                              ("large-media", args.large_count, args.large_mib * 1024**2)]:
        with tempfile.TemporaryDirectory(prefix="photoforge-bench-") as folder:
            root = Path(folder)
            # JPEG's established fallback accepts these synthetic bytes.
            # Every unique size is still fully hashed; no user media is read.
            for i in range(count):
                path = root / f"IMG_20240102_030405_{i:06d}.jpg"
                with path.open("wb") as stream:
                    stream.write(i.to_bytes(8, "big"))
                    remaining = size - 8
                    block = b"x" * min(1024**2, remaining)
                    while remaining:
                        stream.write(block[:remaining])
                        remaining -= min(len(block), remaining)
            baseline = None
            for workers in (1, 4):
                times = []
                peak = 0
                for _ in range(args.repeats):
                    tracemalloc.start()
                    started = time.perf_counter()
                    scan = scan_directory(root, hash_workers=workers)
                    times.append(time.perf_counter() - started)
                    peak = max(peak, tracemalloc.get_traced_memory()[1])
                    tracemalloc.stop()
                    plan, groups = run_pipeline(root, scan_result=scan)
                    value = (scan, plan, groups, render_json_report(plan))
                    if baseline is None:
                        baseline = value
                    assert value == baseline, "serial/parallel output mismatch"
                results.append(dict(dataset=name, files=count, bytes_per_file=size,
                                    workers=workers, median_seconds=statistics.median(times),
                                    peak_python_bytes=peak, equivalent=True))
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
