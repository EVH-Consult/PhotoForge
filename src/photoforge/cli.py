from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cli_reporting import render_diff, render_summary, render_duplicate_details
from .model import CorruptFile
from .naming import load_naming_rules
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
    parser.add_argument("--naming-config", metavar="rules.json",
                        help="Explicit version-1 filename and folder templates")
    parser.add_argument("--hash-workers", type=int, choices=range(1, 33), default=1,
                        metavar="1..32", help="Bounded parallel full-content hashing (default: 1)")
    parser.add_argument("--verbosity", choices=("quiet", "normal", "verbose"), default="normal",
                        help="Console detail level; JSON is never reduced")
    parser.add_argument("--progress", action="store_true", help="Emit phase progress on stderr")
    parser.add_argument("--diff", action="store_true", help="Render a dry-run action diff")
    parser.add_argument("--limit", type=int, metavar="N", help="Limit action count in --diff")
    parser.add_argument("--confirm", action="store_true", help="Require interactive approval with --apply")
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

    if args.confirm and not args.apply:
        parser.error("--confirm requires --apply")
    if args.diff and (args.json or args.apply):
        parser.error("--diff requires dry-run console output (no --json or --apply)")
    if args.limit is not None and (not args.diff or args.limit < 1):
        parser.error("--limit requires --diff and a positive integer")

    def progress(message):
        if args.progress:
            print(f"photoforge: {message}", file=sys.stderr)

    input_path = validate_input_path(args.input_path)
    output_path = (
        validate_output_path(args.output) if args.output is not None else None
    )

    naming_rules = load_naming_rules(Path(args.naming_config).expanduser()) if args.naming_config else None
    if naming_rules is not None and args.output is None and naming_rules.folder != "{year}/{month}/{day}":
        raise ValueError("custom folder rules require --output")

    timestamp_policy = (
        load_timestamp_policy(Path(args.timestamp_policy).expanduser().resolve())
        if args.timestamp_policy is not None
        else None
    )
    progress("scanning")
    scan_result = scan_directory(input_path, timestamp_policy=timestamp_policy, hash_workers=args.hash_workers)

    corrupt_files = [
        CorruptFile(path=s.path, error_type=s.reason)
        for s in scan_result.skipped
        if s.reason.startswith("corrupt_")
    ]

    progress("planning")
    plan_result, contextual_grouping = run_pipeline(
        input_path,
        output_path=output_path,
        corrupt_files=corrupt_files,
        scan_result=scan_result,
        naming_rules=naming_rules,
    )

    if args.json:
        report = render_json_report(
            plan_result,
            contextual_grouping=contextual_grouping,
            include_context=args.context,
        )
    elif args.diff:
        report = render_diff(plan_result, limit=args.limit)
    elif args.verbosity == "quiet":
        report = render_summary(plan_result)
    else:
        report = render_console_report(
            plan_result,
            contextual_grouping=contextual_grouping,
            include_context=args.context,
        )
    # Must always print report before any filesystem changes
    print(report, flush=True)
    if args.verbosity == "verbose":
        print(render_summary(plan_result), file=sys.stderr)
        details = render_duplicate_details(plan_result)
        if details:
            print(details, file=sys.stderr)
    progress("report complete")

    if args.apply:
        if args.confirm:
            if not sys.stdin.isatty():
                raise ValueError("confirmation requires interactive stdin; no changes applied")
            print("Apply this plan? [y/N] ", end="", file=sys.stderr, flush=True)
            answer = sys.stdin.readline().strip().casefold()
            if answer not in {"y", "yes"}:
                print("Plan declined; no changes applied.", file=sys.stderr)
                return 1
        progress("applying")
        apply_actions(plan_result.actions)
        progress("application complete")

    return 0


def entrypoint(argv: list[str] | None = None) -> int:
    """CLI error boundary; main() remains the exception-based library API."""
    effective = sys.argv[1:] if argv is None else argv
    try:
        return main(effective)
    except (ValueError, OSError) as exc:
        code = "invalid_input" if isinstance(exc, ValueError) else "filesystem_error"
        message = str(exc) if isinstance(exc, ValueError) else "filesystem operation failed"
        if "--json" in effective:
            print(json.dumps({"error": {"code": code, "message": message}},
                             ensure_ascii=False, sort_keys=True), file=sys.stderr)
        else:
            print(f"photoforge: {code}: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(entrypoint())
