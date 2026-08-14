# PhotoForge — Architecture

## Purpose

This document defines the implemented architecture of PhotoForge.

It explains:

- the major runtime components
- the actual end-to-end execution flow
- the data contracts exchanged between components
- the responsibility boundaries between layers

This document describes the system as implemented.
It does not redefine detailed behavior already specified in:

- `README.md`
- `SPEC.md`
- `model.md`
- `scanner.md`
- `planner.md`
- `grouping.md`
- `pipeline.md`

---

## Architectural Principles

PhotoForge follows these architectural principles:

- deterministic execution
- explicit data flow
- immutable model contracts
- strict responsibility separation
- no hidden cross-component behavior
- no implicit planner or grouping side effects

All runtime behavior must be traceable to explicit component interactions.

---

## High-Level Structure

PhotoForge is composed of the following runtime components:

- CLI
- scanner
- pipeline orchestration
- planner
- contextual grouping
- reporter
- operations
- model layer

The model layer defines the shared immutable data contracts used by the runtime components.

---

## Actual End-to-End Execution Flow

Current end-to-end CLI execution is:

1. CLI parses and validates arguments
2. CLI performs one scan
3. CLI derives `CorruptFile` objects from corrupt scanner skips
4. CLI invokes `run_pipeline(...)`, passing the `ScanResult` and planner arguments
5. `run_pipeline(...)` computes contextual grouping from that valid `FileRecord` set
6. `run_pipeline(...)` invokes the planner with the same records
7. CLI passes `PlanResult` and `ContextualGrouping` to the reporter
8. CLI prints the report
9. CLI optionally executes planned actions via `operations.py` when `--apply` is enabled

Expressed structurally:

    CLI
      ├─ validate_input_path(...)
      ├─ validate_output_path(...)           [optional]
      ├─ scan_directory(input_path)          [single shared scan]
      ├─ derive CorruptFile from skipped corrupt entries
      ├─ run_pipeline(
      │      input_path,
      │      output_path=...,
      │      corrupt_files=...,
      │      scan_result=...,
      │  )
      │    ├─ reuse scan_result.records
      │    ├─ build_contextual_grouping(records)
      │    └─ plan_files(records, output_path=..., corrupt_files=...)
      ├─ render_console_report(...) or render_json_report(...)
      ├─ print(report)
      └─ apply_actions(...)                  [only if --apply]

The CLI reuses one scan snapshot for corrupt-file reporting, contextual
grouping, and planning. Library callers that omit `scan_result` receive one
internal scan.

---

## Component Architecture

### 1. CLI (`cli.py`)

#### 1.1 Responsibilities

The CLI is responsible for:

- parsing command-line arguments
- validating input and output paths
- performing the scan used by corrupt-file derivation and the pipeline
- deriving `CorruptFile` objects from scanner output
- invoking pipeline orchestration
- selecting report format
- printing the rendered report
- optionally invoking filesystem actions

#### 1.2 Corrupt-File Transformation

The CLI performs the only runtime transformation from scanner diagnostics into planner-layer corrupt-file objects.

Transformation rule:

- include each `SkippedFile` whose `reason` starts with `"corrupt_"`
- map:
  - `CorruptFile.path = SkippedFile.path`
  - `CorruptFile.error_type = SkippedFile.reason`

Important:

- `ScanIssue` is not used for this transformation
- this transformation is outside the scanner boundary
- this transformation is outside the pipeline orchestration boundary

#### 1.3 Boundary

The CLI does not:

- define scanner behavior
- define planner behavior
- define grouping rules
- define report rendering logic
- define filesystem action semantics

Its non-trivial runtime role is orchestration at application level and corrupt-file derivation.

---

### 2. Scanner (`scanner.py`)

#### 2.1 Responsibilities

The scanner is responsible for:

- validating the input directory
- recursively discovering filesystem entries
- classifying discovered paths
- reading file metadata
- extracting timestamps
- normalizing metadata
- hashing processable files
- constructing `FileRecord`
- classifying corrupt files
- collecting `SkippedFile` and `ScanIssue`
- returning `ScanResult`

#### 2.2 Output

The scanner returns:

    ScanResult:
        records: tuple[FileRecord, ...]
        skipped: tuple[SkippedFile, ...]
        issues: tuple[ScanIssue, ...]
        total_entries_seen: int
        supported_files_processed: int

#### 2.3 Boundary

The scanner does not:

- construct `CorruptFile`
- perform duplicate grouping
- perform contextual grouping
- perform planning
- render reports
- execute filesystem actions

The scanner is a deterministic producer of valid records and diagnostics only.

---

### 3. Pipeline Orchestration (`pipeline.py`)

#### 3.1 Responsibilities

The pipeline orchestration layer is responsible for:

- accepting a supplied scan snapshot or performing one scan when none is supplied
- obtaining the valid `FileRecord` set from `ScanResult.records`
- computing contextual grouping exactly once from that valid record set
- invoking the planner exactly once
- forwarding planner arguments and keyword arguments unchanged
- returning `PlanResult` and `ContextualGrouping` separately

#### 3.2 Behavior

`run_pipeline(...)` performs:

1. use the supplied `scan_result`, or call `scan_directory(input_path)` once
2. `records = scan_result.records`
3. `grouping = build_contextual_grouping(records)`
4. `plan_result = plan_files(records, *planner_args, **planner_kwargs)`
5. `return plan_result, grouping`

#### 3.3 Boundary

The pipeline orchestration layer does not:

- derive corrupt files from scanner output
- inspect or reinterpret `scan_result.skipped`
- inspect or reinterpret `scan_result.issues`
- render reports
- execute actions
- merge contextual grouping into `PlanResult`

It is a partial orchestration layer, not the full end-to-end application controller.

---

### 4. Planner (`planner.py`)

#### 4.1 Responsibilities

The planner is responsible for:

- sorting valid input records deterministically
- grouping files by identical SHA-256
- selecting exactly one canonical file per duplicate group
- generating canonical filenames
- resolving target paths
- classifying canonical-file actions
- constructing `PlannedRecord`
- constructing `PlannedAction`
- carrying `CorruptFile` through `PlanResult` without reinterpretation

#### 4.2 Input

The planner consumes:

- valid `FileRecord`
- optional `CorruptFile`

#### 4.3 Output

The planner returns:

    PlanResult:
        records: tuple[PlannedRecord, ...]
        actions: tuple[PlannedAction, ...]
        corrupt_files: tuple[CorruptFile, ...]

#### 4.4 Boundary

The planner does not:

- scan the filesystem for input discovery
- derive corrupt files
- inspect `ScanResult`
- perform contextual grouping
- render reports
- execute actions

The planner is the deterministic transformation from validated planning inputs to planning output.

---

### 5. Contextual Grouping (`grouping.py`)

#### 5.1 Responsibilities

Contextual grouping is responsible for:

- consuming the valid `FileRecord` set
- building deterministic `record_ref` values
- constructing `ContextualGroup`
- constructing `ContextualGrouping`

#### 5.2 Boundary

Contextual grouping:

- uses only valid `FileRecord`
- excludes corrupt files and skipped files
- does not affect duplicate grouping
- does not affect canonical selection
- does not affect action classification
- does not modify `PlanResult`

It is an independent structural output layer.

---

### 6. Reporter (`reporter.py`)

#### 6.1 Responsibilities

The reporter is responsible for:

- building summary output from `PlanResult`
- rendering deterministic console output
- rendering deterministic JSON output
- optionally including contextual grouping when requested

#### 6.2 Input

The reporter consumes:

- `PlanResult`
- optional `ContextualGrouping`

#### 6.3 Boundary

The reporter does not:

- derive planning behavior
- alter model objects
- classify corrupt files
- compute grouping
- execute filesystem actions

It is a pure rendering layer.

---

### 7. Operations (`operations.py`)

#### 7.1 Responsibilities

Operations are responsible for:

- consuming planned actions
- applying filesystem changes when explicitly requested

#### 7.2 Boundary

Operations do not:

- determine which actions should occur
- re-evaluate collisions
- inspect corrupt-file semantics
- derive planner decisions

Operations execute planner intent; they do not redefine it.

---

### 8. Model Layer (`model.py`)

#### 8.1 Responsibilities

The model layer defines the immutable shared contracts exchanged between components.

Core model objects:

- `FileRecord`
- `CorruptFile`
- `PlannedRecord`
- `PlannedAction`
- `PlanResult`
- `ContextualGroup`
- `ContextualGrouping`

#### 8.2 Boundary

The model layer:

- defines structure and structural invariants
- does not implement scanner logic
- does not implement planning logic
- does not implement grouping algorithms
- does not render output
- does not execute actions

---

## Data Flow Architecture

### A. Shared Scan: Corrupt Derivation Path

The CLI passes this scan result into the pipeline.

Flow:

    scan_directory(input_path)
        -> ScanResult
        -> scan_result.skipped
        -> filter reason startswith("corrupt_")
        -> CorruptFile[]

This path exists to derive planner-layer corrupt-file input.

---

### B. Shared Scan: Planning and Grouping Path

The CLI-supplied `ScanResult` is consumed inside `run_pipeline(...)`.

Flow:

    shared ScanResult
        -> scan_result.records
        -> valid FileRecord[]

That valid record set is the shared source for:

- contextual grouping
- planning

---

### C. Planning Path

Flow:

    FileRecord[]
    + CorruptFile[]        [forwarded from CLI]
        -> plan_files(...)
        -> PlanResult

---

### D. Grouping Path

Flow:

    FileRecord[]
        -> build_contextual_grouping(...)
        -> ContextualGrouping

---

### E. Reporting Path

Flow:

    PlanResult
    + ContextualGrouping   [optional inclusion]
        -> render_console_report(...) or render_json_report(...)
        -> output string

---

### F. Execution Path

Flow:

    PlanResult.actions
        -> apply_actions(...)
        -> filesystem changes

This occurs only when `--apply` is enabled.

---

## Single-Snapshot Architecture

Normal CLI execution performs one scan. The CLI uses that `ScanResult` to
derive `CorruptFile` values and passes the same snapshot into
`run_pipeline(...)`.

The shared snapshot provides:

- `scan_result.skipped` for corrupt-file derivation
- `scan_result.records` for contextual grouping and planning

This prevents the filesystem from being observed at two different moments
during one CLI run. Direct library callers may omit `scan_result`; in that
case `run_pipeline(...)` performs one scan itself.

---

## Responsibility Boundaries

### CLI ↔ Scanner

- CLI invokes scanner
- scanner returns `ScanResult`
- CLI interprets only `scan_result.skipped` for corrupt-file derivation

### CLI ↔ Pipeline

- CLI invokes `run_pipeline(...)`
- CLI forwards `scan_result` and planner arguments such as `output_path` and `corrupt_files`

### Pipeline ↔ Scanner

- pipeline reuses the supplied `ScanResult` during normal CLI execution
- pipeline invokes scanner once only when a library caller omits `scan_result`
- pipeline consumes `scan_result.records`

### Pipeline ↔ Planner

- pipeline forwards valid records and planner arguments unchanged
- pipeline does not inspect planner internals

### Pipeline ↔ Grouping

- pipeline computes grouping exactly once from the complete valid record set
- grouping remains separate from planner output

### CLI ↔ Reporter

- CLI selects output format
- reporter renders but does not print
- CLI prints before any filesystem changes

### CLI ↔ Operations

- CLI invokes operations only after report rendering
- operations consume only planned actions

---

## Determinism Architecture

Determinism is preserved through explicit architectural choices:

- scanner discovery order is explicit
- scanner output ordering is explicit
- planner input ordering is normalized
- planner group ordering is explicit
- planner action ordering is explicit
- contextual grouping ordering is explicit
- reporter output is derived from deterministic model values
- pipeline orchestration order is fixed
- lazy dependency loading in pipeline uses explicit candidate order

The architecture permits no random or implicit stateful behavior.

---

## Non-Goals

The implemented architecture does not include:

- perceptual duplicate detection
- metadata rewriting
- file deletion
- overwrite behavior
- concurrency
- external integrations
- hidden background state
- embedded contextual grouping inside planner results

---

## Architectural Summary

PhotoForge is not a single monolithic pipeline.

It is a deterministic runtime composition of:

- CLI-level preprocessing and application control
- scanner-level discovery and enrichment
- pipeline-level orchestration for valid-record processing
- planner-level deterministic action generation
- grouping-level independent structural output
- reporter-level rendering
- operations-level execution

The most important architectural facts are:

- corrupt-file derivation occurs at CLI level
- planning and contextual grouping are coordinated by `run_pipeline(...)`
- corrupt derivation, planning, and grouping use one shared scan snapshot
- contextual grouping is independent from planner behavior
- all components interact only through explicit data contracts

---

## Final Contract

The implemented architecture must preserve the following:

1. scanner produces valid-file and diagnostic output only
2. CLI derives `CorruptFile` explicitly from corrupt scanner skips
3. CLI passes its `ScanResult` to pipeline orchestration; direct library calls may let the pipeline scan once
4. planner consumes valid records and propagated corrupt files
5. contextual grouping is computed separately and does not alter planner output
6. reporter renders output without changing model semantics
7. operations execute planned actions only when explicitly requested

No component may silently assume responsibilities owned by another component.

