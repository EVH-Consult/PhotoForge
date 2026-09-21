# PhotoForge — PNG Metadata Extractor

## Classification

INTERNAL

---

## Purpose

Provides metadata extraction for PNG files.

---

## Responsibilities

- return readable EXIF timestamp candidates
- append the deterministic filesystem `mtime` candidate

---

## Inputs

- file path

---

## Outputs

- timestamp and timestamp source (format defined by caller)

---

## Determinism Constraints

- identical file content must yield identical extracted metadata

---

## Non-Responsibilities

- no normalization
- no cross-source resolution
- no corrupt-file classification
- no FileRecord construction
- no planner or grouping interaction

---

## Integration Boundary

Used by:

- metadata extraction layer

---

## Final Contract

Returns EXIF candidates followed by filesystem fallback without defining
system-level resolution behavior.
