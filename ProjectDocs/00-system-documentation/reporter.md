# PhotoForge — Reporter

## Classification

BOUNDARY

---

## Purpose

The reporter module renders deterministic output from planning results.

It converts model objects into:

- console output
- JSON output

It does not define behavior, only representation.

---

## Primary Functions

- build_summary(...)
- render_console_report(...)
- render_json_report(...)

---

## Responsibilities

The reporter is responsible for:

- computing summary statistics
- rendering human-readable console output
- rendering structured JSON output
- optionally including contextual grouping
- including structured timestamp metadata and batch contexts

---

## Summary Computation

    build_summary(plan_result) -> dict

Computes:

- total files processed
- duplicate groups
- total duplicates
- planned renames
- planned moves
- planned skips
- collisions
- corrupt file count

Implementation: :contentReference[oaicite:5]{index=5}  

---

## Console Rendering

    render_console_report(plan_result, contextual_grouping, include_context)

Behavior:

- builds ordered text output
- includes summary
- lists canonical planned actions
- lists corrupt files
- optionally includes contextual grouping

Rules:

- requires contextual_grouping if include_context=True :contentReference[oaicite:6]{index=6}  
- deterministic ordering based on input data
- console output preserves the ordering of `plan_result.records` as provided by the planner

---

## JSON Rendering

    render_json_report(...)

Behavior:

- serializes:
  - summary
  - records
  - actions
  - corrupt_files
  - batch_contexts
  - optional contextual_groups

- JSON output is serialized with fixed indentation of 2 spaces
- JSON object keys are serialized in lexicographic order

Ordering rules:

- the ordering of `records` in JSON output is preserved from `PlanResult.records`
- the ordering of `actions` in JSON output is preserved from `PlanResult.actions`
- the ordering of `corrupt_files` in JSON output is preserved from `PlanResult.corrupt_files`
- only JSON object keys are re-ordered lexicographically
- list-valued output is not re-sorted by the reporter

- uses recursive conversion:

  - dataclasses → dict
  - timestamp candidates → naive/aware/UTC representations plus provenance
  - Path → string
  - datetime → formatted string
  - timedelta → signed offset string

Implementation: :contentReference[oaicite:7]{index=7}  

---

## Inputs

- PlanResult
- optional ContextualGrouping
- include_context flag

---

## Outputs

- string (console or JSON)

---

## Determinism Constraints

The reporter must be deterministic:

- identical inputs → identical output
- stable ordering
- stable formatting
- no environment-dependent behavior

---

## Non-Responsibilities

The reporter does not:

- compute planning decisions
- modify model objects
- classify corrupt files
- compute grouping
- execute actions

---

## Integration Boundary

Used by CLI:

- CLI selects output format
- CLI prints result
- reporter does not perform I/O

---

## Contextual Grouping Handling

Rules:

- included only if explicitly requested
- must be provided when requested
- does not affect planning output

---

## Final Contract

The reporter must:

1. render deterministic output from model objects
2. preserve ordering and structure
3. include contextual grouping only when requested

It is a pure rendering layer.
