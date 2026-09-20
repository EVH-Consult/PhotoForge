# PhotoForge — Metadata Extraction Layer

## Classification

INTERNAL

---

## Purpose

This document defines the metadata extraction layer as a formal system structure.

It establishes:

- the structure of metadata extractors
- the interface contract for extractors
- the boundary between extraction and downstream processing
- the alignment rules for EXIF and non-JPEG formats

This document describes the implemented extraction structure. Exact behaviour
remains authoritative in `SPEC.md`, implementation and tests.

---

## Current System State

All extraction resides under ``src/photoforge/metadata_extractors/``. The
package contains EXIF/JPEG, XMP sidecar, filename, folder, filesystem, HEIC,
PNG, RAW and video extractors. `scanner.py` orchestrates them;
`timestamp_resolution.py` owns cross-source precedence; `metadata.py` owns
normalization. The former standalone `src/photoforge/exif.py` had no supported
consumer and was removed under EVHC-291.

---

## Target Structure

The metadata extraction package is the single location for extraction logic:

- all metadata extraction must be routed through this layer
- no module outside the layer may access format-specific extraction logic directly

---

## Extractor Location

All format-specific extractors must reside under:

```bash
src/photoforge/metadata_extractors/
```

Each format must have a dedicated extractor.

Implemented extractors include:

- ``extract_heic_timestamp``
- ``extract_png_timestamp``
- ``extract_raw_timestamp``
- ``extract_video_timestamp``
- ``extract_exif_metadata`` / ``extract_exif_context``
- ``extract_jpeg_timestamp``
- ``extract_xmp_metadata``
- ``extract_filename_timestamp``
- ``extract_folder_timestamp``
- ``extract_filesystem_timestamp_candidates``

---

## Extractor Interface

Format timestamp extractors implement:

```python
(path: Path, mtime_timestamp: float) -> tuple[TimestampCandidate, ...]
```

Inputs:

- ``path``: file path
- ``mtime_timestamp``: filesystem timestamp (float)

Outputs:

- zero or more structured timestamp candidates

---

## Extractor Behavior Constraints

Extractors must:

- be deterministic
- produce identical output for identical input
- depend only on:
  - provided path
  - provided timestamp
  - file content (if used)

Extractors must not:

- perform normalization
- perform cross-source fallback beyond defined extractor scope
- modify filesystem state
- depend on global or environment-specific state
- introduce implicit logic

---

## Current Extractor Behavior

Existing non-JPEG format extractors:

- do not read embedded metadata
- deterministically fallback to filesystem timestamp
- return a filesystem candidate

Example:

```python
return extract_filesystem_timestamp_candidates(path, mtime_timestamp)
```

This behavior is explicitly defined and must remain unchanged.

---

## Layer Boundary

The metadata extraction layer must:

- select extractor based on file format
- invoke the extractor
- return raw extracted metadata

The layer must not:

- perform normalization
- perform comparison
- perform diagnostics

---

## Integration with Metadata Module

The metadata module

- validates structure
- enforces deterministic metadata shape
- does not perform extraction

Pipeline order:

``
extractors → policy → resolution → normalize_metadata → FileRecord
``

The extraction layer operates strictly before normalization.

---

## EXIF Alignment

Alignment is complete. The active EXIF path is
``metadata_extractors/exif.py`` through ``metadata_extractors/jpeg.py``. There
is no standalone compatibility module or supported `photoforge.exif` API.

---

## Invariants

- Existing runtime behavior must remain unchanged
- Timestamp output must remain:
  - naive datetime
  - deterministic
- Extractors must not introduce:
  - implicit fallback
  - timezone inference
- Format-specific logic must remain isolated within extractors

---

## Non-Responsibilities

The metadata extraction layer does not:

- normalize metadata
- define fallback precedence across sources
- compare timestamps
- classify inconsistencies
- construct pipeline objects

---

## Final Contract

The metadata extraction layer defines:

1. extractor structure
2. extractor interface
3. extraction boundary

It ensures that metadata extraction is:

- explicit
- deterministic
- isolated from downstream processing
