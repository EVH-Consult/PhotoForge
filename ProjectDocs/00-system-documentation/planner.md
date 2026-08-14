# PhotoForge — Planner

## Purpose

The planner is the deterministic transformation engine of PhotoForge.

It transforms a set of valid `FileRecord` objects into a complete, immutable execution plan represented as `PlanResult`.

The planner is responsible for:

- grouping files by identical content (SHA-256)
- selecting a canonical file per duplicate group
- generating canonical filenames
- resolving target paths
- assigning action classifications
- producing a deterministic planning result
- propagating corrupt files without interpretation

The planner does **not**:

- scan the filesystem for input files
- extract EXIF metadata
- compute hashes
- classify corrupt files
- perform contextual grouping
- modify files

---

## Input

The planner consumes:

- `Iterable[FileRecord]`
- `Iterable[CorruptFile]` (optional, default empty)

Function:

    plan_files(
        records: Iterable[FileRecord],
        output_path: Path | None = None,
        corrupt_files: Iterable[CorruptFile] = (),
    ) -> PlanResult

### Requirements

All input `FileRecord` objects must:

- satisfy all model invariants
- be fully enriched
- represent valid, processable files

All `CorruptFile` objects must:

- be pre-classified
- not correspond to any `FileRecord`
- not require further interpretation

The planner does not validate or derive corrupt files.

---

## Output

The planner returns a `PlanResult`.

Definition:

    @dataclass(frozen=True)
    class PlanResult:
        records: tuple[PlannedRecord, ...]
        actions: tuple[PlannedAction, ...]
        corrupt_files: tuple[CorruptFile, ...]

All collections are immutable tuples.

---

## Planner Pipeline

The planner executes the following deterministic steps.

---

### 1. Sort Input Records

All `FileRecord` objects are sorted lexicographically by:

    str(record.path)

This ensures deterministic behavior.

---

### 2. Group by SHA-256

Records are grouped by:

    record.sha256

Rules:

- one group per unique hash
- groups sorted lexicographically by hash
- records inside each group sorted lexicographically by path

---

### 3. Select Canonical File

Exactly one file per group is selected.

Selection criteria (in order):

1. largest file size
2. prefer a timestamp source whose identifier starts with `exif_`
3. lexicographically smallest path

Ranking key:

    (-size, exif_priority, str(path))

Where:

    exif_priority = 0 if timestamp_source.startswith("exif_") else 1

Canonical file is the minimum of this key.

---

### 4. Generate Canonical Filename

Format:

    YYYY-MM-DD_HHMMSS_<short-hash>.jpg

Rules:

- timestamp derived from canonical file
- `<short-hash>` = first 8 characters of SHA-256
- extension always `.jpg` (lowercase)
- no variation allowed

---

### 5. Resolve Target Path

If `output_path` is `None`:

    target = source.parent / canonical_filename

If `output_path` is provided:

    target = output_path / YYYY / MM / DD / canonical_filename

Where:

- YYYY = year
- MM = month
- DD = day
- derived from canonical timestamp

---

### 6. Classify Action

Only canonical files are evaluated.

Decision order:

1. if source_path == target_path → `skip`
2. if target_path exists → `collision`
3. if output_path is None → `rename`
4. otherwise → `move`

---

### 7. Assign Duplicate Behavior

For non-canonical files:

- `canonical = False`
- `target_path = None`
- `action_status = "duplicate"`

Duplicates do not produce actions.

---

### 8. Build PlannedRecord

Each input `FileRecord` produces exactly one `PlannedRecord`.

Fields include:

- group id (`sha256`)
- group size
- canonical flag
- canonical filename
- target path (if canonical)
- action status
- original metadata fields

---

### 9. Build PlannedAction

Each canonical file produces one `PlannedAction`.

Fields:

- `source_path`
- `target_path`
- `action`

Duplicates do not produce actions.

---

### 10. Output Ordering

Planner output is deterministic but not globally sorted.

Ordering rules:

- duplicate groups are processed in lexicographic SHA-256 order
- records within each group are processed in lexicographic path order

Emission rules:

- `records` are emitted in duplicate-group iteration order
- `actions` are emitted in canonical-record group iteration order
- `corrupt_files` are sorted lexicographically by path

---

## Corrupt File Handling

The planner does not derive or interpret corrupt files.

Behavior:

- accepts `CorruptFile` as input
- includes them unchanged in `PlanResult`
- ensures deterministic ordering

Rules:

- corrupt files must not produce `PlannedRecord`
- corrupt files must not produce `PlannedAction`
- corrupt files must not influence grouping or canonical selection

---

## Determinism Guarantees

For identical input:

- identical grouping
- identical canonical selection
- identical filenames
- identical target paths
- identical action classification
- identical output ordering

The planner output is deterministic because:

- input records are sorted lexicographically by path before grouping
- duplicate groups are processed in lexicographic SHA-256 order
- records within each group are sorted lexicographically by path
- `corrupt_files` are sorted by path before inclusion in `PlanResult`

No final global sort is applied to `records` or `actions`.

The planner must not depend on:

- filesystem traversal order
- environment state
- randomness

---

## Constraints

- duplicate grouping is based strictly on SHA-256 equality
- no perceptual hashing
- no file deletion
- no overwriting existing files
- no concurrency
- no external state

Filesystem interaction is limited to:

    target_path.exists()

for collision detection.

---

## Integration Boundary

The planner operates on model objects only.

Upstream:

- scanner produces `FileRecord`
- CLI derives `CorruptFile`

Downstream:

- reporter consumes `PlanResult`
- operations execute `PlannedAction`

The planner does not interact with:

- `ScanResult`
- `SkippedFile`
- `ScanIssue`

---

## Final Contract

The planner is a pure, deterministic transformation:

    (FileRecord[], CorruptFile[]) -> PlanResult

It defines:

- what actions should occur
- how files are grouped and named

It does not execute those actions and does not modify input data.
