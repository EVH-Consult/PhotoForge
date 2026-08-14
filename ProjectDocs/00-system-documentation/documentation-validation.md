# Documentation Validation Procedure

## Purpose

This document defines the deterministic procedure for validating documentation coverage and consistency.

The goal is to ensure that:

* all runtime modules are documented
* all documentation reflects actual implementation
* no behavior is undocumented
* no documentation contradicts implementation

Documentation must be treated as a verified representation of the system, not a best-effort description.

---

## Scope

This procedure applies:

* after each milestone (partial validation)
* before every release (full validation, mandatory)

---

## Definitions

### Module

A Python file under:

``
src/photoforge/
``

Only Python source files (*.py) are considered modules.

Directories, non-Python files, and cache artifacts must be ignored.

---

### Module Documentation

A markdown file under `ProjectDocs/00-system-documentation/` corresponding
to the module name or documented subsystem.

Mapping rule:

``src/photoforge/<path>/<module>.py``
→ ``ProjectDocs/00-system-documentation/<path>/<module>.md``

Examples:

src/photoforge/scanner.py
→ ProjectDocs/00-system-documentation/scanner.md

src/photoforge/metadata_extractors/heic.py
→ ProjectDocs/00-system-documentation/metadata_extractors/heic.md

This mapping is mandatory.

Any deviation from this mapping is a validation failure.

---

## Validation Rules

### Rule 1 — Complete Module Coverage

Every module must have a corresponding documentation file.

No exceptions.

---

### Rule 2 — Single Source of Truth

Each module must be documented in exactly one corresponding file.

No duplication across multiple module-level documents.

---

### Rule 3 — Tiered Documentation Depth

Each module must be classified as:

* CORE
* BOUNDARY
* INTERNAL

This classification determines documentation depth.

---

### Rule 4 — Implementation is Authoritative

If documentation and code differ:

* the code is correct
* the documentation must be updated

---

### Rule 5 — No Hidden Behavior

Any behavior present in code must be explicitly documented.

---

### Rule 6 — No Undocumented Assumptions

Documentation must not introduce behavior that is not implemented.

---

### Rule 7 — Deterministic Wording

Documentation must avoid:

* vague language
* implied behavior
* assumptions not enforced by code

---

## Validation Procedure

If any step detects a failure condition, validation must stop immediately and return REJECTED.

No further steps may be executed after a blocking failure is detected.

---

### Step 0 — Freeze Validation Scope

The validation scope is defined strictly as:

* all modules under src/photoforge/
* all corresponding module documentation
* generic documentation:

  * README.md
  * SPEC.md
  * ProjectDocs/00-system-documentation/architecture.md

Only Python source files (*.py) are considered modules.

Scope must not change once validation begins.

---

### Step 1 — Enumerate Modules

List all modules:

```bash
find src/photoforge -name "*.py"
```

This list defines the complete validation scope.

---

### Step 2 — Enforce Module → Doc Mapping

For each module:

``src/photoforge/<path>/<module>.py``
→ ``ProjectDocs/00-system-documentation/<path>/<module>.md``

Check:

* documentation file exists
* relative path matches module path exactly
* file name matches module name exactly

Failure conditions:

* missing documentation file
* mismatched relative path
* mismatched file name

---

### Step 3 — Classify Module Tier

Each module must be classified as:

CORE — defines core system behavior
BOUNDARY — defines orchestration or external interaction
INTERNAL — defines supporting functionality

Examples:

CORE:

* scanner
* planner
* grouping
* pipeline
* model

BOUNDARY:

* cli
* reporter
* operations

INTERNAL:

* metadata
* exif
* hashing
* metadata_extractors/*

This classification must be reflected in the documentation.

---

### Step 4 — Validate Module Documentation

All modules:

* must reflect current implementation
* must not contradict code
* must not contain outdated behavior
* must not omit implemented behavior

CORE modules must include:

* responsibilities
* full behavior description
* execution flow
* invariants
* integration boundaries

BOUNDARY modules must include:

* responsibilities
* integration points
* explicit transformations (if any)
* clear boundaries

INTERNAL modules must include:

* purpose
* responsibilities
* inputs / outputs
* determinism constraints
* explicit non-responsibilities

INTERNAL modules must not:

* define system-level behavior
* duplicate higher-level documentation

---

### Step 5 — Validate Generic Documentation

The following documents must always be validated:

* README.md
* SPEC.md
* ProjectDocs/00-system-documentation/architecture.md

Check:

* consistency with implementation
* consistency with module documentation
* no contradictions
* no missing behavior

---

### Step 6 — Build Coverage Matrix

Construct mapping:

``src/photoforge/<path>/<module>.py``
→ ``ProjectDocs/00-system-documentation/<path>/<module>.md``
→ referenced in generic docs where required by tier

Reference requirements:

CORE modules must be referenced in:

* SPEC.md
* ProjectDocs/00-system-documentation/architecture.md

BOUNDARY modules must be referenced in:

* ProjectDocs/00-system-documentation/architecture.md

Additionally:

If a BOUNDARY module performs transformations that affect:

* planner input
* pipeline orchestration
* output rendering

then it must also be referenced in:

* SPEC.md

INTERNAL modules:

* do not require direct reference in generic docs
* must not introduce system-level behavior in generic documentation

---

### Step 7 — Detect Coverage Gaps

Identify modules where documentation exists but does not describe all implemented behavior.

If detected:

* extend existing documentation

Missing documentation files must already have been caught in Step 2.

---

### Step 8 — Detect Documentation Drift

Identify:

* documentation describing non-existent behavior
* implementation behavior not documented
* inconsistent terminology across documents

All drift must be resolved before validation passes.

---

### Step 9 — Produce Validation Result

Output must be:

``
Status: ACCEPTED / REJECTED
``

If REJECTED:

* list missing documentation
* list mismatches
* list inconsistencies

Release must not proceed if status is REJECTED.

---

## Partial Validation (Post-Milestone)

After each milestone:

* identify affected modules
* run Steps 2–4 for affected modules only
* update generic documentation if impacted

---

## Full Validation (Pre-Release)

Before release:

* run full procedure (Steps 1–9)
* no skipped modules
* no partial checks allowed

---

## Final Rule

Documentation is valid if and only if:

* every module is documented
* documentation matches implementation
* no behavior is undocumented
* no contradictions exist across documents

If any condition fails:

documentation is invalid
release is blocked
