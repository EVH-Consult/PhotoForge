from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from photoforge.model import (
    ContextualGroup,
    ContextualGrouping,
    validate_contextual_group,
    validate_contextual_grouping,
)

TESTS_E2E_ROOT = Path(__file__).resolve().parent
FIXTURES_ROOT = TESTS_E2E_ROOT / "fixtures"
GOLDEN_ROOT = TESTS_E2E_ROOT / "golden"
MANIFESTS_ROOT = TESTS_E2E_ROOT / "manifests"

INPUT_ROOT_PLACEHOLDER = "<INPUT_ROOT>"
OUTPUT_ROOT_PLACEHOLDER = "<OUTPUT_ROOT>"


class E2EError(RuntimeError):
    """Raised when the deterministic E2E harness encounters invalid state."""

def _stabilize_e2e_temp_paths(text: str) -> str:
    stabilized = text.replace("\r\n", "\n").replace("\\", "/")

    stabilized = re.sub(
        r"[A-Za-z]:/{1,2}Users/{1,2}[^/]+/{1,2}AppData/{1,2}Local/{1,2}Temp/{1,2}(?:photoforge-e2e-[^/]+|photoforge-e2e/{1,2}[^/]+)/{1,2}input",
        INPUT_ROOT_PLACEHOLDER,
        stabilized,
    )

    stabilized = stabilized.replace(f"{INPUT_ROOT_PLACEHOLDER}//", f"{INPUT_ROOT_PLACEHOLDER}/")
    stabilized = stabilized.replace(f"{OUTPUT_ROOT_PLACEHOLDER}//", f"{OUTPUT_ROOT_PLACEHOLDER}/")
    return stabilized

def fixture_ids() -> tuple[str, ...]:
    fixture_ids_list = sorted(
        path.stem
        for path in MANIFESTS_ROOT.glob("*.json")
        if path.is_file()
    )
    return tuple(fixture_ids_list)


def load_manifest(fixture_id: str) -> dict[str, Any]:
    manifest_path = MANIFESTS_ROOT / f"{fixture_id}.json"
    if not manifest_path.is_file():
        raise E2EError(f"Manifest not found for fixture: {fixture_id}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    if data.get("fixture_id") != fixture_id:
        raise E2EError(
            f"Manifest fixture_id mismatch for {fixture_id}: {data.get('fixture_id')!r}"
        )

    input_dir = data.get("input_dir")
    if not isinstance(input_dir, str) or input_dir == "":
        raise E2EError(f"Manifest input_dir is invalid for fixture: {fixture_id}")

    scenarios = data.get("scenarios")
    if not isinstance(scenarios, dict):
        raise E2EError(f"Manifest scenarios is invalid for fixture: {fixture_id}")

    fixture_mtime_utc = data.get("fixture_mtime_utc")
    if not isinstance(fixture_mtime_utc, str):
        raise E2EError(f"Manifest fixture_mtime_utc is invalid for fixture: {fixture_id}")
    try:
        parsed_mtime = datetime.fromisoformat(fixture_mtime_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise E2EError(
            f"Manifest fixture_mtime_utc is invalid for fixture: {fixture_id}"
        ) from exc
    if parsed_mtime.tzinfo is None:
        raise E2EError(
            f"Manifest fixture_mtime_utc must include a timezone: {fixture_id}"
        )

    determinism_runs = scenarios.get("determinism_runs")
    if not isinstance(determinism_runs, int) or determinism_runs < 1:
        raise E2EError(
            f"Manifest determinism_runs must be >= 1 for fixture: {fixture_id}"
        )

    return data


def fixture_input_source_dir(fixture_id: str) -> Path:
    manifest = load_manifest(fixture_id)
    source_dir = Path(manifest["input_dir"])

    if not source_dir.is_absolute():
        source_dir = Path.cwd() / source_dir

    source_dir = source_dir.resolve(strict=False)

    if not source_dir.is_dir():
        raise E2EError(f"Fixture input directory not found: {source_dir}")

    return source_dir


def golden_dir(fixture_id: str) -> Path:
    return GOLDEN_ROOT / fixture_id


def ensure_golden_dir(fixture_id: str) -> Path:
    path = golden_dir(fixture_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_fixture_to_temp(fixture_id: str) -> Path:
    source_dir = fixture_input_source_dir(fixture_id)

    temp_root = Path(tempfile.gettempdir()) / "photoforge-e2e" / fixture_id
    if temp_root.exists():
        shutil.rmtree(temp_root)

    temp_root.mkdir(parents=True, exist_ok=True)
    target_dir = temp_root / "input"
    shutil.copytree(source_dir, target_dir)

    fixture_mtime = datetime.fromisoformat(
        load_manifest(fixture_id)["fixture_mtime_utc"].replace("Z", "+00:00")
    ).timestamp()
    for path in sorted(target_dir.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_file():
            os.utime(path, (fixture_mtime, fixture_mtime))

    return target_dir


def normalize_text_paths(
    text: str,
    *,
    input_root: Path,
    output_root: Path | None = None,
) -> str:
    normalized = text.replace("\r\n", "\n")

    def _variants(path: Path) -> tuple[str, ...]:
        raw = str(path)
        slash = raw.replace("\\", "/")
        doubleslash = raw.replace("\\", "//")
        return tuple(sorted({raw, slash, doubleslash}, key=len, reverse=True))

    for variant in _variants(input_root):
        normalized = normalized.replace(variant, INPUT_ROOT_PLACEHOLDER)

    if output_root is not None:
        for variant in _variants(output_root):
            normalized = normalized.replace(variant, OUTPUT_ROOT_PLACEHOLDER)

    normalized = normalized.replace("\\", "/")
    return normalized


def canonicalize_for_json(
    value: Any,
    *,
    input_root: Path,
    output_root: Path | None = None,
) -> Any:
    if is_dataclass(value):
        return canonicalize_for_json(
            asdict(value),
            input_root=input_root,
            output_root=output_root,
        )

    if isinstance(value, dict):
        return {
            str(key): canonicalize_for_json(
                value[key],
                input_root=input_root,
                output_root=output_root,
            )
            for key in sorted(value.keys(), key=str)
        }

    if isinstance(value, (list, tuple)):
        return [
            canonicalize_for_json(
                item,
                input_root=input_root,
                output_root=output_root,
            )
            for item in value
        ]

    if isinstance(value, Path):
        text = str(value)
        return normalize_text_paths(
            text,
            input_root=input_root,
            output_root=output_root,
        )

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    return value


def dump_canonical_json(
    value: Any,
    *,
    input_root: Path,
    output_root: Path | None = None,
) -> str:
    normalized_value = canonicalize_for_json(
        value,
        input_root=input_root,
        output_root=output_root,
    )
    return json.dumps(
        normalized_value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temp_path, path)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def assert_exact_match(*, actual: str, expected_path: Path) -> None:
    import difflib

    expected = read_text(expected_path)

    actual_stable = _stabilize_e2e_temp_paths(actual)
    expected_stable = _stabilize_e2e_temp_paths(expected)

    if actual_stable != expected_stable:
        diff_lines = list(
            difflib.unified_diff(
                expected_stable.splitlines(),
                actual_stable.splitlines(),
                fromfile=str(expected_path),
                tofile="actual",
                lineterm="",
                n=3,
            )
        )

        diff_preview = "\n".join(diff_lines[:200])
        raise AssertionError(
            f"Exact match failed for {expected_path}.\n"
            f"Expected length={len(expected_stable)}, actual length={len(actual_stable)}.\n"
            f"Diff preview:\n{diff_preview}"
        )

def validate_grouping_invariants(grouping: ContextualGrouping) -> None:
    validate_contextual_grouping(grouping)
    for group in grouping.groups:
        validate_contextual_group(group)
        if not isinstance(group, ContextualGroup):
            raise E2EError("Grouping contains a non-ContextualGroup item")


def run_cli_capture(
    *,
    input_root: Path,
    extra_args: list[str] | None = None,
) -> str:
    args = [
        sys.executable,
        "-m",
        "photoforge.cli",
        str(input_root),
    ]
    if extra_args:
        args.extend(extra_args)

    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    stdout_text = completed.stdout.replace("\r\n", "\n")
    stderr_text = completed.stderr.replace("\r\n", "\n")

    if completed.returncode != 0:
        raise E2EError(
            "PhotoForge CLI failed.\n"
            f"Command: {args}\n"
            f"Exit code: {completed.returncode}\n"
            f"STDOUT:\n{stdout_text}\n"
            f"STDERR:\n{stderr_text}"
        )

    if stderr_text:
        raise E2EError(f"Unexpected stderr output:\n{stderr_text}")

    return stdout_text


def run_pipeline_models(
    *,
    input_root: Path,
    context_enabled: bool,
) -> dict[str, Any]:
    from photoforge.model import CorruptFile
    from photoforge.pipeline import run_pipeline
    from photoforge.scanner import scan_directory

    scan_result = scan_directory(input_root)

    corrupt_files = [
        CorruptFile(path=item.path, error_type=item.reason)
        for item in scan_result.skipped
        if item.reason.startswith("corrupt_")
    ]

    plan_result, contextual_grouping = run_pipeline(
        input_root,
        output_path=None,
        corrupt_files=corrupt_files,
    )

    return {
        "scan_result": scan_result,
        "contextual_grouping": contextual_grouping,
        "plan_result": plan_result,
    }

def build_models_json(
    *,
    input_root: Path,
    context_enabled: bool,
    output_root: Path | None = None,
) -> str:
    model_payload = run_pipeline_models(
        input_root=input_root,
        context_enabled=context_enabled,
    )

    grouping = model_payload.get("contextual_grouping")
    if isinstance(grouping, ContextualGrouping):
        validate_grouping_invariants(grouping)

    return dump_canonical_json(
        model_payload,
        input_root=input_root,
        output_root=output_root,
    )


def scenario_outputs(
    *,
    fixture_id: str,
) -> dict[str, str]:
    input_root = copy_fixture_to_temp(fixture_id)

    default_console = normalize_text_paths(
        run_cli_capture(input_root=input_root),
        input_root=input_root,
    )

    default_json = normalize_text_paths(
        run_cli_capture(input_root=input_root, extra_args=["--json"]),
        input_root=input_root,
    )

    context_console = normalize_text_paths(
        run_cli_capture(input_root=input_root, extra_args=["--context"]),
        input_root=input_root,
    )

    context_json = normalize_text_paths(
        run_cli_capture(input_root=input_root, extra_args=["--json", "--context"]),
        input_root=input_root,
    )

    models_json = build_models_json(
        input_root=input_root,
        context_enabled=True,
    )

    return {
        "default.console.txt": default_console,
        "default.json": default_json,
        "context.console.txt": context_console,
        "context.json": context_json,
        "models.json": normalize_text_paths(
            models_json,
            input_root=input_root,
        ),
    }

