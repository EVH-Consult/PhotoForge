# Contextual Grouping

---

## Purpose

Contextual grouping defines a deterministic transformation from a set of valid `FileRecord` objects to a structured `ContextualGrouping` output.

It maps:

    tuple[FileRecord, ...] -> ContextualGrouping

This transformation is:

- deterministic
- pure with respect to grouping computation
- reproducible
- independent of duplicate grouping and planner decisions

Contextual grouping is an additional structural output of the pipeline.
It does not modify planner behavior.

---

## Responsibility Boundary

### Input

Contextual grouping consumes only valid `FileRecord` objects.

Requirements:

- all inputs must already satisfy `FileRecord` model invariants
- corrupt files must not be included
- skipped files must not be included
- no partial records are allowed

### Output

Contextual grouping produces one `ContextualGrouping` object.

The output must satisfy all structural invariants defined by `model.py` and documented in `model.md`.

### Contextual grouping does not

- modify `FileRecord`
- read the filesystem
- inspect skipped files
- inspect corrupt files
- perform duplicate grouping
- perform canonical selection
- influence action planning
- generate rename or move actions
- modify reporting behavior unless explicitly requested by CLI flags
- access external systems or environment state

---

## Role in the System

Contextual grouping is a separate structural layer in the PhotoForge pipeline.

It is computed from the same valid `FileRecord` set used by the planner, but it is not part of duplicate grouping and does not affect planner results.

Current pipeline role:

- scanner produces valid `FileRecord` objects
- planner produces `PlanResult`
- contextual grouping is computed separately from valid `FileRecord`
- reporter may include contextual grouping output when requested
- CLI exposes this optional output through `--context`

This means contextual grouping is integrated into the active pipeline, but remains behaviorally independent from planning.

---

## Execution Model

Contextual grouping is executed as a deterministic sequence:

1. consume the complete valid `FileRecord` set
2. order records by:
   - primary key: `timestamp` ascending
   - secondary key: `str(path)` ascending
3. partition the ordered sequence into maximal consecutive groups
4. two consecutive records belong to the same group if:

       (current_record.timestamp - previous_record.timestamp).total_seconds() <= 300

5. build `ContextualGroup` objects
6. assemble the final `ContextualGrouping`

This execution order is fixed conceptually and matches the implemented behavior.

---

## Record Reference Model

Contextual grouping does not embed full `FileRecord` objects in the output.

Instead, each grouped file is referenced through `record_ref`.

Definition:

- `record_ref = str(file_record.path)`

Properties:

- derived deterministically from the POSIX-style path relative to the common
  scanned root, so relocating an unchanged dataset does not change group IDs
- stable for identical `FileRecord.path`
- independent of object identity
- independent of scan order

Constraints:

- `record_ref` must not be empty
- `record_ref` values within a group must be unique
- `record_ref` values across groups must not overlap

---

## Group Identifier Model

Each contextual group has a deterministic `group_id`.

Definition:

- `group_id` is derived only from `member_refs`

Computation:

1. encode `member_refs` as canonical JSON
2. use UTF-8 encoding
3. use no whitespace variation
4. compute SHA-256 of the encoded bytes
5. represent the result as lowercase hexadecimal

Properties:

- deterministic
- stable for identical `member_refs`
- delimiter-safe
- independent of filesystem state
- independent of runtime conditions

---

## Structural Guarantees

The produced `ContextualGrouping` must satisfy all of the following.

### Coverage

- all input `FileRecord` objects must be represented exactly once through their `record_ref`

### Exclusivity

- a `record_ref` must not appear in more than one group

### Non-emptiness

- each `ContextualGroup` must contain at least one member

### Member ordering

- `member_refs` must be sorted lexicographically

### Member uniqueness

- `member_refs` within a group must be unique

### Group ordering

- `groups` must be sorted lexicographically by `group_id`

### Group identifier integrity

- each `group_id` must equal the deterministic value computed from its `member_refs`

### Group identifier uniqueness

- no two groups may have the same `group_id`

These are model-level invariants and must always hold.

---

## Determinism Guarantees

For identical input `FileRecord` sets, contextual grouping must produce identical:

- `record_ref` values
- group membership
- member ordering
- `group_id` values
- group ordering
- final `ContextualGrouping` structure

Grouping must not depend on:

- scan traversal order
- object identity
- filesystem ordering
- randomness
- locale
- environment variables
- external services
- mutable runtime state

No implicit ordering is allowed.

---

## Metadata Constraints

Contextual grouping may only depend on the metadata fields allowed by the implemented grouping design.

Current allowed metadata fields are:

- `timestamp`
- `timestamp_source`

No other metadata fields may influence grouping in this version.

In particular, contextual grouping must not depend on:

- SHA-256 duplicate grouping structure
- file size
- EXIF fields other than the normalized timestamp outcome
- planner action classifications
- target paths
- reporter state

---

## Relationship to Duplicate Grouping

Contextual grouping is separate from duplicate grouping.

Duplicate grouping:

- groups files by identical SHA-256
- drives canonical selection
- drives planning output

Contextual grouping:

- groups valid files by contextual rules defined in the implementation
- produces a separate structural output
- does not alter duplicate groups
- does not alter canonical selection
- does not alter action classification

The two grouping layers must remain independent.

---

## Relationship to Planner

Contextual grouping does not influence the planner.

Specifically, contextual grouping must not:

- change canonical-file selection
- change canonical filename generation
- change target path resolution
- change collision detection
- change action status
- change `PlanResult`

The planner can be fully understood without contextual grouping.
Contextual grouping is additive output only.

---

## Relationship to Reporter

The reporter accepts contextual grouping separately from `PlanResult`.

Rules:

- contextual grouping output is optional in reports
- contextual grouping must be included only when explicitly requested
- if contextual output is requested, a valid `ContextualGrouping` must be provided
- if contextual output is not requested, reporting behavior remains unchanged except for the absence of contextual sections

This preserves backward-compatible planning semantics while allowing additional structured output.

---

## Relationship to CLI

The CLI exposes contextual grouping through the `--context` flag.

Behavior:

- contextual grouping is computed by the pipeline
- reporter includes contextual grouping only when `--context` is enabled
- absence of `--context` suppresses contextual grouping from rendered output
- `--context` does not change planning behavior
- `--context` does not change scanner behavior
- `--context` does not change action execution behavior

This flag controls report inclusion, not grouping semantics.

---

## Integration Boundary

At runtime, the implemented system follows this high-level grouping flow:

    scan_directory(...) -> ScanResult
    plan_files(scan_result.records, ..., corrupt_files=...) -> PlanResult
    compute_contextual_grouping(scan_result.records) -> ContextualGrouping
    reporter(plan_result, contextual_grouping, include_context=...)
    
Contextual grouping is computed from the valid `FileRecord` set only.

Corrupt files are excluded because they do not become `FileRecord`.

Skipped non-corrupt files are excluded for the same reason.

---

## Empty Input Behavior

If the input `FileRecord` set is empty, contextual grouping must be represented as:

    ContextualGrouping(groups=())

No synthetic groups may be created.

---

## Model Contract Reference

The structural contract for contextual grouping is defined by the model layer.

This includes:

- `ContextualGroup`
- `ContextualGrouping`
- `record_ref` validation
- `member_refs` ordering and uniqueness
- `group_id` determinism
- cross-group exclusivity

This document defines the role, boundaries, and system integration of contextual grouping.

The precise structure and invariants are defined in the model contract and must not be contradicted here.

---

## Scope

This document defines:

- the purpose of contextual grouping
- its place in the pipeline
- its boundaries
- its determinism guarantees
- its relationship to planner, reporter, and CLI
- its structural obligations at system level

This document does not redefine:

- the full model contract
- dataclass field definitions already defined in `model.py`
- low-level helper implementation details unrelated to behavior

Grouping rules themselves must match the implementation and any authoritative architecture documentation.

---

## Final Contract

Contextual grouping is a deterministic, independent structural transformation over valid `FileRecord` objects.

It must:

- consume only valid `FileRecord`
- produce a structurally valid `ContextualGrouping`
- remain independent from duplicate grouping and planner behavior
- be reproducible for identical input
- be exposed only as optional reporting output
- never alter action planning or execution
