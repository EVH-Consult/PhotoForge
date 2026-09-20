# PhotoForge v0.1 — Implementation Plan

> Historical implementation sequence for v0.1. It is not the current module
> map or work plan. Current work is owned by Jira and current behaviour by
> implementation plus `SPEC.md`. EXIF extraction now lives under
> `metadata_extractors/exif.py`; the former standalone `src/photoforge/exif.py`
> was removed by EVHC-291 after reference verification found no active consumer.

## Principles

- Follow `SPEC.md` exactly, no redesign, no feature creep
- Build strictly bottom-up
- Each step must be testable in isolation
- No filesystem mutation before dry-run is correct
- Determinism is mandatory at every stage

## Implementation Order

1. `model.py`
2. `exif.py`
3. `hashing.py`
4. `scanner.py`
5. `planner.py`
6. `reporter.py`
7. Wire dry-run `cli.py`
8. `operations.py`
9. Wire `--apply`

## Milestones

### 1. Model Layer (`model.py`)

Define all dataclasses:

- `FileRecord`
- `PlannedRecord`
- `PlannedAction`
- `PlanResult`

Rules:

- Use `Path`, not `str`
- No business logic
- No optional fields unless specified

Test:

- Instantiation works
- No mutable defaults

### 2. EXIF Extraction (`exif.py`)

Implement:

- EXIF parsing
- Fallback chain:
  1. `DateTimeOriginal`
  2. `DateTimeDigitized`
  3. `DateTime`
  4. `mtime`

Returns:

- `(datetime, timestamp_source)`

Test:

- All fallback paths
- Invalid EXIF handled
- Correct source labels

### 3. Hashing (`hashing.py`)

Implement:

- SHA-256 full file hashing

Test:

- Known hash values
- Empty file
- Output format: 64-character lowercase hex

### 4. Scanner — Discovery + Enrichment (`scanner.py`)

Implement:

- Recursive file discovery
- Supported file filtering (JPEG only)
- Deterministic ordering
- Metadata extraction (size, mtime timestamp)
- Timestamp extraction via EXIF module
- Hash computation
- Build complete `FileRecord`

Test:

- Unsupported files skipped
- Errors are per-file, non-fatal
- Deterministic output
- Identical files produce identical hash

### 5. Planner — Grouping + Canonical Selection (`planner.py`)

Implement:

- Group by `sha256`
- Deterministic ordering
- Canonical selection

Ranking key:

`(-record.size, 0 if record.timestamp_source != "mtime" else 1, str(record.path))`

Test:

- One canonical per group
- Tie-breakers strictly respected
- Stable results across runs

### 6. Planner — Naming + Actions (`planner.py`)

Extend planner.

Implement:

- Canonical filename:
  `YYYY-MM-DD_HHMMSS_<short-hash>.jpg`
- Target path resolution:
  - in-place
  - organized: `<output>/<YYYY>/...`
- Action classification:
  - `skip`
  - `rename`
  - `move`
  - `collision`
- Duplicates:
  - no action
  - `target_path = None`

Test:

- Filename format exact
- Collision detection correct
- Duplicates untouched
- Actions match spec exactly

### 7. Reporter (`reporter.py`)

Implement:

- Console summary
- JSON output

Must include:

- summary counts
- planner records
- planner actions
- scanner diagnostics

Test:

- Correct counts
- JSON serialization (`Path` and `datetime` handled)
- Deterministic output

### 8. CLI — Dry Run (`cli.py`)

Wire:

`scan → plan → report`

Rules:

- Dry-run default
- No filesystem mutation

Test:

- End-to-end run
- Mixed datasets (duplicates, errors, skips)

### 9. Operations (`operations.py`)

Implement:

- Apply `PlannedAction` for canonical files only

Rules:

- No overwrite
- Create directories if needed
- No duplicate modification
- No metadata changes

Test:

- rename works
- move works
- skip and collision do nothing

### 10. CLI — Apply Mode (`cli.py`)

Extend CLI:

- Add `--apply`

Flow:

`scan → plan → report → apply`

Test:

- Dry-run vs apply behavior difference
- Filesystem changes match plan exactly

## Critical Invariants

- Deterministic ordering everywhere
- Scanner returns only complete `FileRecord` objects
- Planner is the single source of truth for actions
- Duplicates are never modified
- Collisions never overwrite
- EXIF fallback strictly enforced
- Output schema matches `SPEC.md` exactly

## Common Pitfalls

- Using filesystem iteration order (non-deterministic)
- Treating duplicates as actions
- Overwriting collisions
- Mixing planner logic into scanner or CLI
- Returning partial records
- Accepting non-standard EXIF formats
- Forgetting `.jpg` normalization
- Leaking `Path` or `datetime` into JSON

## Execution Guidance

Do not:

- Jump ahead to CLI before planner is correct
- Implement apply before dry-run is validated
- Add convenience abstractions

Do:

- Validate each layer independently
- Keep modules strictly separated
- Stop and fix determinism issues immediately

## Status

- Design: complete
- Specification: frozen
- Next step: implementation
