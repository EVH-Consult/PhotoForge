# PhotoForge

PhotoForge is a deterministic command-line tool for scanning media files, extracting timestamps, detecting exact duplicates, and generating a canonical rename and organization plan.

The system is designed to be:

- deterministic (identical input → identical output)
- safe (dry-run by default)
- explicit (no hidden heuristics)
- reproducible (no environment-dependent behavior)

---

## Version

Current version: v0.7-dev
Status: development

This version includes:

- deterministic scanner pipeline
- deterministic EXIF/XMP/filename/folder/filesystem timestamp resolution
- explicit timestamp correction/inference policies and structured diagnostics
- exact duplicate detection (SHA-256)
- canonical file selection and planning
- corrupt file classification and reporting
- location-independent contextual grouping (optional structural output)

---

## Specification

- `SPEC.md` defines the current behavior contract
- Historical specifications (`SPEC_vx.x.md`) are not authoritative

All behavior described in this README must be consistent with `SPEC.md` and the implementation.

---

## Scope

PhotoForge provides a deterministic pipeline with the following stages:

1. scanning
2. metadata extraction and normalization
3. hashing
4. duplicate grouping
5. canonical selection
6. planning (rename/move/skip/collision)
7. optional contextual grouping
8. reporting

---

## Installation

```bash
pip install .
```

For development:

```bash
pip install -e .
```

---

## CLI Usage

```bash
photoforge <input_path> [--output <output_path>] [--json] [--apply] [--context]
           [--timestamp-policy <policy.json>]
```

### Arguments

- `<input_path>`  
  Root directory to scan (required)

### Flags

- `--output <output_path>`  
  Target root directory for organized output  
  If omitted, files are renamed in place

- `--json`  
  Output deterministic JSON instead of console format

- `--apply`  
  Execute planned filesystem operations  
  If omitted, runs in dry-run mode

- `--context`  
  Include contextual grouping in output  
  Does not affect planning behavior

- `--timestamp-policy <policy.json>`
  Apply an explicit, versioned timestamp correction/inference policy.
  The policy is read-only and never rewrites media metadata

---

## Pipeline Overview

### 1. Scanner

- recursively scans input directory
- classifies filesystem entries
- produces:
  - valid `FileRecord` objects
  - skipped files
  - diagnostic issues

#### File classification

The scanner distinguishes:

- **processable files**
  - JPEG: `.jpg`, `.jpeg`
  - PNG: `.png`
  - HEIC/HEIF: `.heic`, `.heif`
  - TIFF: `.tif`, `.tiff`
  - RAW: `.cr2`, `.nef`, `.arw`
  - video: `.mp4`, `.mov`

- **unsupported files**
  - all other extensions

#### Corrupt files

A file is classified as corrupt if it cannot be fully processed:

- metadata unreadable
- timestamp cannot be resolved
- file unreadable
- hashing fails

Corrupt files:

- do not produce `FileRecord`
- are tracked deterministically
- are reported separately

Newly supported non-JPEG formats receive deterministic structural validation.
PNG and TIFF are verified through Pillow; HEIC/HEIF, RAW and video inputs use
their documented container/signature checks. JPEG keeps its established
metadata/fallback behavior unchanged.

#### Apple Live Photos

A Live Photo is paired only when one JPEG/HEIC/HEIF still and one MOV have the
same case-sensitive stem in the same directory. A valid pair is planned and
deduplicated as one logical asset, uses the still timestamp, and receives one
shared canonical basename with format-preserving extensions. Unpaired files are
processed independently. Ambiguous candidates are left independent and produce
deterministic warnings. A collision affecting either component marks both pair
components as collisions.

---

### 2. Metadata Extraction

Timestamp candidates use this strict trust order:

1. EXIF `DateTimeOriginal`, `DateTimeDigitized`, `DateTime`
2. XMP sidecar `CreateDate`, `DateCreated`, `ModifyDate`
3. filename timestamp
4. immediate parent-folder timestamp
5. filesystem `mtime`

All valid candidates are retained in JSON output with their source, precision,
naive value, timezone offset, aware value and UTC value where available.
Date-only filenames/folders resolve at midnight. Invalid high-priority values do
not block deterministic fallback.

An optional version-1 JSON timestamp policy supports exact folder and camera
make/model corrections, configured GPS-region offsets, trusted-device offset
consensus, and a default. The precedence and schema are defined in `SPEC.md`.
See `timestamp-policy.example.json` for a complete non-secret example.
Corrections are explicit input; PhotoForge never silently rewrites EXIF, XMP,
media files or sidecars.

Read-only metadata context also includes camera make/model, keywords, GPS,
sidecar provenance, candidate comparisons and immediate-folder batch
classification. These diagnostics do not alter canonical naming or planning.

---

### 3. Hashing

- SHA-256 over full file content
- exact duplicate detection only
- short hash = first 8 characters

---

### 4. Duplicate Grouping

- ordinary files are grouped by their SHA-256
- Live Photos are grouped by a deterministic asset hash derived from the still
  and motion SHA-256 values
- one group per unique file or asset hash
- groups of size > 1 are duplicates

---

### 5. Canonical Selection

Exactly one file per group is selected using:

1. largest file size
2. prefer EXIF timestamp over `mtime`
3. lexicographically smallest path

---

### 6. Planning

For each file:

- canonical file → action:
  - `rename`
  - `move`
  - `skip`
  - `collision`

- duplicate files:
  - never modified
  - marked as `duplicate`

Target structure:

- in-place (default):
  - rename in same directory

- organized mode (`--output`):
  - `<output>/<YYYY>/<MM>/<DD>/<filename>`

Filename format:

```text
YYYY-MM-DD_HHMMSS_<short-hash>.<normalized-format-extension>
```

JPEG remains normalized to `.jpg`; TIFF is normalized to `.tif`; other formats
retain their supported extension. Both components of a Live Photo use the same
basename and their own extensions.

---

### 7. Corrupt File Propagation

Corrupt files are:

- identified by the scanner
- transformed into `CorruptFile` objects at CLI level
- passed into the planning pipeline
- included in `PlanResult`
- reported but never modified

They:

- do not participate in grouping
- do not produce actions
- do not affect planning decisions

---

### 8. Contextual Grouping (Optional)

Contextual grouping is a deterministic structural grouping of valid files based on metadata.

Properties:

- computed from `FileRecord` set
- independent from duplicate grouping
- does not affect planning
- produces `ContextualGrouping`

Output is included only when:

```bash
--context
```

---

### 9. Reporting

Two output modes:

- console (default)
- JSON (`--json`)

Output includes:

- summary
- planned actions
- duplicate information
- corrupt files

If `--context` is enabled:

- contextual grouping is included

---

## Safety Model

- dry-run is default
- no filesystem changes without `--apply`
- files are never overwritten
- collisions are detected and skipped
- duplicate files are never modified
- all actions are fully computed before execution

---

## Determinism

Within the documented supported-media contract, PhotoForge enforces:

- identical input → identical output
- explicit ordering everywhere
- no randomness
- UTC-normalized filesystem fallback behavior
- contextual identifiers based on paths relative to the scanned root

This applies to:

- scanning
- grouping
- canonical selection
- filename generation
- planning
- reporting

---

## Constraints

- exact duplicate detection only (SHA-256)
- no perceptual hashing
- no file deletion
- no overwriting existing files
- no metadata rewriting
- no concurrency
- no external state

---

## Notes

- behavior is strictly defined by implementation and `SPEC.md`
- historical specifications are not authoritative
- this version introduces extended internal structure while preserving deterministic guarantees

---

## Warning

When using `--apply`, PhotoForge performs real filesystem changes.

Before applying:

- run a dry-run
- review planned actions
- test on a small dataset
- ensure backups exist
