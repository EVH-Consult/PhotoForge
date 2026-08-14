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
- EXIF extraction and UTC-normalized filesystem fallback
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
  - `.jpg`, `.jpeg`

- **recognized but not processable**
  - `.png`, `.heic`, `.heif`, `.cr2`, `.nef`, `.arw`, `.mp4`, `.mov`
  - recorded but not processed

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

---

### 2. Metadata Extraction

- EXIF-based timestamp extraction with strict fallback chain:
  1. `DateTimeOriginal`
  2. `DateTimeDigitized`
  3. `DateTime`
  4. filesystem `mtime`

- metadata is normalized into a consistent internal representation
- timestamps are stored as naive UTC values; EXIF offsets and filesystem
  timestamps are converted to UTC before timezone information is removed
- invalid timestamps cause processing failure and are treated as corrupt files

---

### 3. Hashing

- SHA-256 over full file content
- exact duplicate detection only
- short hash = first 8 characters

---

### 4. Duplicate Grouping

- files grouped by identical SHA-256
- one group per unique hash
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
YYYY-MM-DD_HHMMSS_<short-hash>.jpg
```

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

Within the documented JPEG input contract, PhotoForge enforces:

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
