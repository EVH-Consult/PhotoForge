# PhotoForge — Model Contract

## Purpose

The model layer defines the immutable data structures exchanged between scanner, planner, reporter, CLI, and operations.

These models are the canonical in-memory contract of the PhotoForge pipeline.

The model layer does **not**:

- scan files
- read EXIF
- compute hashes
- plan actions
- render reports
- modify the filesystem

It only defines the data shapes and their invariants.

---

## Design Principles

All model objects must be:

- immutable
- deterministic
- explicit
- free of side effects

Rules:

- all models use frozen dataclasses
- all paths are `Path`
- all timestamps are naive `datetime`
- no model may contain partial or ambiguous state
- no model may mix valid-file and corrupt-file semantics

---

## Pipeline Overview

The model layer supports this high-level flow:

1. scanner produces `FileRecord`
2. scanner classifies corrupt files separately
3. planner consumes valid `FileRecord`
4. planner produces `PlannedRecord` and `PlannedAction`
5. planner carries `CorruptFile` separately in `PlanResult`
6. reporter renders `PlanResult`
7. operations executes `PlannedAction`

---

## Core Models

### 1. FileRecord

Represents one fully valid, fully enriched input file discovered by the scanner.

A `FileRecord` must only exist if:

- file path is valid
- metadata was read successfully
- timestamp was resolved successfully
- hash was computed successfully

Definition:

```python
@dataclass(frozen=True)
class FileRecord:
    path: Path
    size: int
    timestamp: datetime
    timestamp_source: str
    sha256: str
    short_hash: str
```

#### 1.1 Field Semantics

- `path`
  - absolute normalized path to the source file
- `size`
  - file size in bytes
- `timestamp`
  - canonical timestamp after EXIF fallback resolution
- `timestamp_source`
  - source used to derive `timestamp`
- `sha256`
  - full SHA-256 digest of file content
- `short_hash`
  - first 8 characters of `sha256`

#### 1.2 Invariants

- `path` is expected to be absolute
- `size` must be non-negative
- `sha256` must be a 64-character lowercase hex string
- `short_hash` must equal `sha256[:8]`
- `timestamp_source` must be one of:
  - `exif_datetimeoriginal`
  - `exif_datetimedigitized`
  - `exif_datetime`
  - `mtime`

#### 1.3 Responsibility Boundary

Produced by:

- scanner

Consumed by:

- planner

Not used for:

- corrupt files
- partial scan failures

Path invariant note:

- the absolute-path property is established by scanner construction
- it is not validated by model-layer runtime checks

---

### 2. CorruptFile

Represents one file that could not be fully processed through the scanner pipeline.

A `CorruptFile` must only exist if:

- the file was supported for processing
- processing failed deterministically
- no `FileRecord` was created for that file

Definition:

```python
@dataclass(frozen=True)
class CorruptFile:
    path: Path
    error_type: str
```

#### 2.1 Field Semantics

- `path`
  - absolute normalized path to the corrupt file
- `error_type`
  - deterministic classification of the failure

#### 2.2 Allowed `error_type` values (v0.3)

- `corrupt_metadata_unreadable`
- `corrupt_timestamp_unresolved`
- `corrupt_file_unreadable`
- `corrupt_hash_failed`

#### 2.3 Invariants

- `path` must be absolute
- `error_type` must be deterministic
- the same file must not exist as both `FileRecord` and `CorruptFile`

#### 2.4 Responsibility Boundary

Produced by:

- scanner (classification)
- CLI/planner layer (propagation)

Consumed by:

- planner (carry only, never plan)
- reporter

Not used for:

- unsupported files
- symlinks
- non-regular files

---

### 3. PlannedRecord

Represents one valid file after duplicate grouping and planning.

Every `PlannedRecord` corresponds to exactly one valid `FileRecord`.

Definition:

```python
@dataclass(frozen=True)
class PlannedRecord:
    path: Path
    duplicate_group_id: str
    duplicate_group_size: int
    canonical: bool
    canonical_filename: str
    target_path: Path | None
    action_status: str
    sha256: str
    short_hash: str
    timestamp: datetime
    timestamp_source: str
```

#### 3.1 Field Semantics

- `path`
  - original source path of the valid file
- `duplicate_group_id`
  - group identifier derived from SHA-256
- `duplicate_group_size`
  - number of valid files in the duplicate group
- `canonical`
  - whether this record is the canonical file of the group
- `canonical_filename`
  - deterministic filename selected for the group
- `target_path`
  - destination path for canonical file, otherwise `None`
- `action_status`
  - planner classification of what should happen
- `sha256`
  - full SHA-256 digest
- `short_hash`
  - first 8 characters of SHA-256
- `timestamp`
  - canonical timestamp copied from `FileRecord`
- `timestamp_source`
  - timestamp source copied from `FileRecord`

#### 3.2 Invariants

- `duplicate_group_id` must equal `sha256`
- `duplicate_group_size` must be at least 1
- `canonical_filename` must be deterministic for the group
- if `canonical is True`:
  - `target_path` must not be `None`
  - `action_status` must be one of:
    - `rename`
    - `move`
    - `skip`
    - `collision`
- if `canonical is False`:
  - `target_path` must be `None`
  - `action_status` must be `duplicate`

#### 3.4 Responsibility Boundary

Produced by:

- planner

Consumed by:

- reporter

Not used for:

- corrupt files
- unsupported files
- skipped files

---

### 4. PlannedAction

Represents one filesystem action for a canonical file.

Definition:

```python
@dataclass(frozen=True)
class PlannedAction:
    source_path: Path
    target_path: Path
    action: str
```

#### 4.1 Field Semantics

- `source_path`
  - original canonical file path
- `target_path`
  - planned destination path
- `action`
  - exact planner action classification

#### 4.2 Allowed `action` values

- `rename`
- `move`
- `skip`
- `collision`

#### 4.3 Invariants

- only canonical files may produce `PlannedAction`
- `source_path` and `target_path` must be absolute
- operations must not reinterpret planner intent

#### 4.4 Responsibility Boundary

Produced by:

- planner

Consumed by:

- operations
- reporter

Not used for:

- duplicate non-canonical files
- corrupt files

---

### 5. PlanResult

Represents the full deterministic planning output of PhotoForge.

Definition:

```python
@dataclass(frozen=True)
class PlanResult:
    records: tuple[PlannedRecord, ...]
    actions: tuple[PlannedAction, ...]
    corrupt_files: tuple[CorruptFile, ...]
```

All collections in model objects must be tuples to guarantee immutability.

#### 5.1 Field Semantics

- `records`
  - all valid files after planning
- `actions`
  - all canonical-file actions derived from planning
- `corrupt_files`
  - all corrupt files propagated separately

#### 5.2 Invariants

- `records` must contain only valid-file planning output
- `actions` must contain only canonical-file actions
- `corrupt_files` must contain no valid files
- corrupt files must not appear in `records`
- corrupt files must not produce `actions`

#### 5.3 Responsibility Boundary

Produced by:

- planner

Consumed by:

- reporter
- operations (actions only)

---

## 6. Contextual Grouping (v0.5)

Contextual grouping is a structural model that represents a partition of `FileRecord` objects into groups based on contextual similarity.

This model is fully deterministic and independent of grouping construction logic.

---

### Record Reference

A contextual group references `FileRecord` objects indirectly using a stable identifier called `record_ref`.

Definition:

- `record_ref` is the POSIX-style path relative to the grouping root
- `record_ref` is derived deterministically from `FileRecord.path`
- `record_ref` uniquely identifies a `FileRecord` within a scan result

Constraints:

- must not depend on scan order
- must not depend on object identity
- must not require modification of `FileRecord`

---

### ContextualGroup

A `ContextualGroup` is defined as:

```python
@dataclass(frozen=True)
class ContextualGroup:
    group_id: str
    member_refs: tuple[str, ...]
```

Meaning:

- `group_id` is the deterministic identifier of the group
- `member_refs` is the complete ordered set of record references belonging to the group

---

### Group Identifier

The `group_id` is defined as a deterministic identifier derived only from `member_refs`.

Computation:

- encode `member_refs` as a canonical JSON array of strings
  - UTF-8 encoding
  - no whitespace variation
- compute the SHA-256 hash of the encoded value
- represent the result as a hexadecimal string

Properties:

- deterministic
- stable for identical `member_refs`
- independent of external state
- delimiter-safe and unambiguous

---

### ContextualGrouping

A `ContextualGrouping` is defined as:

```python
@dataclass(frozen=True)
class ContextualGrouping:
    groups: tuple[ContextualGroup, ...]
```

Meaning:

- `groups` is the complete ordered set of contextual groups

---

### Structural Invariants

The contextual grouping model must satisfy the following constraints:

Partition:

ContextualGrouping represents a partition of FileRecord objects.

The model enforces:

- no overlap between groups
- valid group structure

Full coverage of all FileRecord objects is a responsibility of the grouping algorithm, not enforced by the model.

- no `FileRecord` may appear in multiple contextual groups

Group constraints:

- each group must contain at least one member
- `member_refs` must be unique within a group
- `member_refs` must be sorted lexicographically

Grouping constraints:

- groups must be sorted lexicographically by `group_id`
- `group_id` must match the deterministic value computed from `member_refs`
- a `record_ref` must not appear in more than one group

---

### Determinism

The contextual grouping model is fully deterministic:

- identical inputs produce identical group structures
- no behavior depends on:
  - scan order
  - filesystem traversal
  - environment
  - external state

---

### Metadata Constraints

Future grouping logic may only use the following metadata:

- `timestamp`
- `timestamp_source`

No other metadata fields are allowed in this version.

---

### Scope

This model defines structure only.

It does not define:

- grouping rules
- grouping thresholds
- grouping algorithms
- grouping execution

These are defined in later milestones.

---

### Empty Input

If no `FileRecord` objects exist, the grouping is represented as:

- an empty tuple of groups

---

## Exclusion Rules

### Corrupt files must never

- become `FileRecord`
- participate in duplicate grouping
- participate in canonical selection
- become `PlannedRecord`
- produce `PlannedAction`

### Unsupported or skipped non-corrupt files must never

- become `CorruptFile`
- are not considered corrupt
- enter planner logic

---

## Determinism Rules

For identical input:

- identical valid files must produce identical `FileRecord`
- identical corrupt cases must produce identical `CorruptFile`
- identical planning input must produce identical `PlannedRecord`
- identical canonical files must produce identical `PlannedAction`
- identical pipeline input must produce identical `PlanResult`

No randomness allowed.

---

## Model Boundary Summary

### scanner → planner

Passes:

- valid files as `FileRecord`
- corrupt files separately for propagation

### planner → reporter

Passes:

- planned valid files as `PlannedRecord`
- canonical actions as `PlannedAction`
- corrupt files as `CorruptFile`

### reporter

Reads model only.
Does not mutate model.

### operations

Consumes only `PlannedAction`.
Does not inspect or derive planning logic.

---

## Final Contract

The model layer must remain:

- minimal
- immutable
- deterministic
- free of policy duplication

Models define **what data exists**, not **how behavior is implemented**.
