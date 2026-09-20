from __future__ import annotations

import argparse
from pathlib import Path

from .model import CorruptFile
from .operations import apply_actions
from .pipeline import run_pipeline
from .reporter import render_console_report, render_json_report
from .scanner import scan_directory
from .timestamp_policy import load_timestamp_policy
from .version import VERSION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="photoforge",
        description=f"PhotoForge {VERSION} - deterministic photo deduplication",
    )
    parser.add_argument(
        "input_path",
        metavar="input_path",
        help="Path to the directory to scan",
    )
    parser.add_argument(
        "--output",
        metavar="output_path",
        help="Path to the output directory root",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Render deterministic JSON output",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute planned filesystem changes",
    )
    parser.add_argument(
        "--context",
        action="store_true",
        help="Include contextual grouping output",
    )
    parser.add_argument(
        "--timestamp-policy",
        metavar="policy.json",
        help="Apply explicit deterministic timestamp correction and inference rules",
    )
    return parser


def validate_input_path(raw_input_path: str) -> Path:
    path = Path(raw_input_path).expanduser()

    if not path.exists():
        raise ValueError(f"Input path does not exist: {path}")

    if not path.is_dir():
        raise ValueError(f"Input path is not a directory: {path}")

    return path.resolve()


def validate_output_path(raw_output_path: str) -> Path:
    path = Path(raw_output_path).expanduser()
    resolved = path.resolve(strict=False)

    if resolved.exists() and not resolved.is_dir():
        raise ValueError(f"Output path is not a directory: {resolved}")

    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = validate_input_path(args.input_path)
    output_path = (
        validate_output_path(args.output) if args.output is not None else None
    )

    timestamp_policy = (
        load_timestamp_policy(Path(args.timestamp_policy).expanduser().resolve())
        if args.timestamp_policy is not None
        else None
    )
    scan_result = scan_directory(input_path, timestamp_policy=timestamp_policy)

    corrupt_files = [
        CorruptFile(path=s.path, error_type=s.reason)
        for s in scan_result.skipped
        if s.reason.startswith("corrupt_")
    ]

    plan_result, contextual_grouping = run_pipeline(
        input_path,
        output_path=output_path,
        corrupt_files=corrupt_files,
        scan_result=scan_result,
    )

    if args.json:
        report = render_json_report(
            plan_result,
            contextual_grouping=contextual_grouping,
            include_context=args.context,
        )
    else:
        report = render_console_report(
            plan_result,
            contextual_grouping=contextual_grouping,
            include_context=args.context,
        )
    # Must always print report before any filesystem changes
    print(report)

    if args.apply:
        apply_actions(plan_result.actions)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
