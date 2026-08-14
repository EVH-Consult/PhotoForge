# PhotoForge — CLI

## Classification

BOUNDARY

## Purpose and responsibilities

`cli.py` is the application entry point. It parses arguments, validates input
and optional output paths, obtains one scanner snapshot, converts corrupt skip
records to `CorruptFile`, invokes the pipeline with that same snapshot, renders
and prints a report, and optionally applies planned actions.

## Interface

`photoforge <input_path> [--output <output_path>] [--json] [--apply] [--context]`

`validate_input_path` expands the user path, requires an existing directory,
and returns its resolved path. `validate_output_path` expands and resolves the
path without requiring it to exist, but rejects an existing non-directory.

## Execution flow

1. Parse arguments and validate paths.
2. Call `scan_directory(input_path)` once.
3. Convert skipped items whose reason starts with `corrupt_` into
   `CorruptFile(path, error_type)`.
4. Call `run_pipeline(..., scan_result=scan_result)`.
5. Render JSON or console output, including context only when requested.
6. Print before performing any filesystem mutation.
7. Call `apply_actions` only when `--apply` is present.
8. Return `0`.

## Boundaries and determinism

The CLI does not define scanning, extraction, planning, grouping, rendering, or
operation semantics. The same `ScanResult` is shared by corrupt derivation,
grouping, and planning, so a normal invocation observes one filesystem snapshot.
Behavior depends only on explicit arguments and that snapshot.
