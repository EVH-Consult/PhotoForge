# PhotoForge — HEIC Metadata Extractor

## Classification

INTERNAL

---

## Purpose

Provides metadata extraction for HEIC files.

This module is part of the metadata extraction layer.

---

## Responsibilities

- return the deterministic filesystem `mtime` candidate for HEIC and HEIF

---

## Inputs

- file path

---

## Outputs

- timestamp and timestamp source (format defined by caller)

---

## Determinism Constraints

- identical file content must yield identical extracted metadata
- no environment-dependent behavior

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

- metadata extraction layer (via metadata module or scanner integration)

---

## Final Contract

Returns filesystem fallback only; embedded HEIF metadata parsing is not claimed.
