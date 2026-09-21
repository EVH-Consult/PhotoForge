# PhotoForge — Video Metadata Extractor

## Classification

INTERNAL

---

## Purpose

Provides metadata extraction for video files.

---

## Responsibilities

- return the deterministic filesystem `mtime` candidate for MP4 and MOV

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
- no fallback logic
- no corrupt-file classification
- no FileRecord construction
- no planner or grouping interaction

---

## Integration Boundary

Used by:

- metadata extraction layer

---

## Final Contract

Returns filesystem fallback only; embedded container metadata parsing is not
claimed.
