# PhotoForge Specification

Status: Accepted  
Version: v0.7-dev
Date: 2026-08-13

This document defines the exact behavior of PhotoForge as implemented.

Implementation is the source of truth.
This specification must reflect actual behavior.

---

## 1. Overview

PhotoForge is a deterministic command-line tool that:

- scans a directory
- extracts and normalizes metadata
- detects exact duplicates (SHA-256)
- identifies corrupt files
- generates a canonical rename and organization plan
- optionally produces contextual grouping output

All behavior is deterministic.

---

## 2. CLI Interface

### Command

```bash
photoforge <input_path> [--output <output_path>] [--json] [--apply] [--context]
           [--timestamp-policy <policy.json>]
```

### Flags

- `--output <output_path>`
- `--json`
- `--apply`
- `--context` (include contextual grouping in output only)
- `--timestamp-policy <policy.json>` (apply an explicit version-1 timestamp policy)

---

## 3. Pipeline Execution

Current end-to-end CLI execution is:

1. CLI validates input and output paths

2. CLI performs one scan:
   scan_directory(input_path)

3. CLI derives CorruptFile objects from skipped entries where:
   reason starts with "corrupt_"

4. CLI invokes the pipeline with the completed scan result:
   run_pipeline(
       input_path,
       output_path=...,
       corrupt_files=...,
       scan_result=...
   )

5. run_pipeline(...) extracts:
   records = scan_result.records

6. run_pipeline(...) computes contextual grouping:
   grouping = build_contextual_grouping(records)

7. run_pipeline(...) invokes planner:
   plan_files(
       records,
       output_path=...,
       corrupt_files=...
   )

8. run_pipeline(...) returns:
   PlanResult, ContextualGrouping

9. CLI renders output using:
    - PlanResult
    - ContextualGrouping

10. CLI optionally executes actions if --apply is enabled

### Single-Snapshot Behavior

The CLI passes its `ScanResult` into the pipeline. Corrupt-file derivation,
planning, and grouping therefore consume the same filesystem snapshot. Direct
library callers may omit `scan_result`; in that case `run_pipeline` performs
exactly one scan.

---

## 4. File Classification

The scanner classifies files into:

### 4.1 Processable

- JPEG: `.jpg`, `.jpeg`
- PNG: `.png`
- HEIC/HEIF: `.heic`, `.heif`
- TIFF: `.tif`, `.tiff`
- RAW: `.cr2`, `.nef`, `.arw`
- video: `.mp4`, `.mov`

These files are fully processed into `FileRecord`.

---

### 4.2 Deterministic format validation

- JPEG retains the established v0.7 metadata/fallback path without a new
  content-validation gate.
- PNG and TIFF must be opened, format-matched and verified by Pillow.
- HEIC/HEIF must contain an ISO Base Media `ftyp` box with an accepted HEIF
  brand.
- CR2 must contain the Canon CR2 little-endian TIFF signature and `CR` marker.
- NEF and ARW must contain a little- or big-endian TIFF signature.
- MP4 and MOV must contain an ISO Base Media `ftyp` box with an accepted MP4 or
  QuickTime brand respectively.

A newly supported file that fails its format validation is corrupt with reason
`corrupt_metadata_unreadable`; it is not downgraded to unsupported.

### 4.3 Unsupported

- all other file types

Behavior:

- recorded as skipped
- not processed further

### 4.4 Format-specific metadata contract

- JPEG, PNG and TIFF: EXIF candidates where readable, then the common XMP,
  filename, folder and filesystem sources.
- HEIC/HEIF, CR2/NEF/ARW and MP4/MOV: the common XMP, filename, folder and
  filesystem sources. Their current format extractors contribute filesystem
  `mtime`; embedded container/RAW metadata parsing is not claimed.
- Every format uses the common normalization, hashing, grouping, planning and
  reporting stages after extraction.
- No extractor rewrites media or metadata.

---

## 5. Corrupt File Definition

A file is corrupt if it is processable but cannot be fully processed.

Corrupt conditions:

- metadata unreadable
- timestamp cannot be resolved
- file unreadable
- hashing failure

Behavior:

- no `FileRecord` is created
- file is recorded as skipped with reason `corrupt_*`
- `ScanIssue` is recorded

### Corrupt File Derivation

CorruptFile objects are derived exclusively in the CLI layer.

Rules:

- derived from SkippedFile entries
- only entries with reason starting with "corrupt_" are included
- mapped as:
  - path → path
  - reason → error_type

The pipeline does not derive or interpret corrupt files.

CorruptFile objects are passed to the planner via keyword arguments.

---

## 6. Corrupt File Propagation

Corrupt files are transformed into `CorruptFile` objects.

Transformation rule:

``
CorruptFile.path = SkippedFile.path
CorruptFile.error_type = SkippedFile.reason
``

Selection rule:

- include only `SkippedFile.reason` values starting with `"corrupt_"`

Notes:

- transformation occurs at CLI layer
- `ScanIssue` is diagnostic only and not used for transformation

---

## 7. Metadata and Timestamp Resolution

### 7.1 Source trust and precedence

Every valid candidate is retained for diagnostics and structured output. The
primary timestamp is the first valid candidate in this fixed source order:

1. EXIF `DateTimeOriginal`, `DateTimeDigitized`, then `DateTime`
2. XMP sidecar `CreateDate`, `DateCreated`, then `ModifyDate`
3. filename timestamp
4. immediate parent-folder timestamp
5. filesystem `mtime`

Input order is preserved inside one source kind. Invalid candidates are ignored
without blocking lower-precedence sources. Date-only filename/folder values are
valid at `00:00:00` and retain `precision = "date"` in structured output.

Filename patterns, in deterministic left-to-right order, are:

- `YYYYMMDD_HHMMSS`
- `YYYY-MM-DD_HH-MM-SS`
- `YYYY-MM-DD HH-MM-SS`
- `YYYYMMDD`
- `YYYY-MM-DD`

Folder patterns use the immediate parent folder only and support `YYYYMMDD`,
`YYYY-MM-DD`, and same-format date ranges. A range uses its first date.

Filesystem fallback uses `mtime`, interpreted as UTC and truncated to seconds.

### 7.2 Structured timestamp representations

Each candidate exposes:

- source kind and detail;
- precision (`date` or `datetime`);
- naive timestamp;
- timezone offset when known;
- aware timestamp and UTC timestamp when the offset is known.

The selected candidate is normalized to a naive UTC value only when a timezone
offset is known. A selected candidate without an offset remains a naive value;
its output does not claim UTC comparability.

### 7.3 Deterministic correction and inference policy

`--timestamp-policy` accepts UTF-8 JSON with `"version": 1`. Supported keys are:

- `default`: optional `timezone_offset` and `clock_correction`;
- `folder_rules`: exact input-relative folder paths plus either correction;
- `device_rules`: exact EXIF make/model pairs plus either correction;
- `gps_rules`: named inclusive latitude/longitude rectangles and a fixed offset.

Offsets use signed `+HH:MM` or `-HH:MM`. Clock correction changes the source
wall-clock value and is never applied to filesystem `mtime`. Filesystem `mtime`
is already interpreted as UTC, so timezone correction and inference are not
applied to it. For all other candidates, timezone selection uses this fixed
order:

1. exact folder rule;
2. exact camera make/model rule;
3. embedded EXIF/XMP offset;
4. the configured GPS rectangle (overlapping matches must agree);
5. trusted-device consensus, but only when every offset-bearing EXIF/XMP
   candidate for that exact make/model has one identical offset;
6. default policy offset.

Folder and device rules are composed per field. A matching higher-precedence
rule that omits `timezone_offset` does not prevent the next matching rule from
supplying it; the same rule applies independently to `clock_correction`.

The policy file is explicit run input. PhotoForge does not consult a network
timezone service, infer daylight-saving rules, or mutate a policy interactively.
Review/correction remains auditable by editing the policy and rerunning.

### 7.4 Metadata context and diagnostics

Read-only metadata context includes camera make/model, EXIF/XMP keywords, GPS
coordinates, the selected XMP sidecar, all timestamp candidates, the correction
basis, and extraction/comparison diagnostics. EXIF/XMP, filename, folder and
filesystem candidates are compared only when they share a representation:
UTC-to-UTC or naive-to-naive.

Immediate folders receive a deterministic batch classification:

- `insufficient_evidence`: one valid media record;
- `event_bounded`: at least two records spanning no more than 24 hours;
- `mixed_content`: at least two records spanning more than 24 hours.

The batch result also records whether any member has a comparable timestamp
inconsistency. It is diagnostic only and does not change planning or grouping.

XMP sidecars are read-only inputs. Keywords and GPS are exposed for inspection
and future explicit naming/grouping contracts; they do not currently change the
canonical filename, target path, or grouping. PhotoForge does not rewrite EXIF,
XMP, media files, or sidecars.

Normalization failure after all candidates are exhausted results in corrupt-file
classification.

---

## 8. Hashing

- SHA-256 over full file content
- lowercase hex digest
- short hash = first 8 characters

---

## 9. Duplicate Grouping

- an ordinary file is one logical asset whose asset hash is its SHA-256
- a paired Live Photo is one logical asset whose asset hash is SHA-256 over the
  ASCII still SHA-256, a NUL separator, and the ASCII motion SHA-256
- assets are grouped by identical asset hash
- groups are sorted deterministically

### 9.1 Apple Live Photo pairing

Pairing is established before planning and uses only the current scan snapshot.
A pair exists only when:

- both files are in the same directory;
- their case-sensitive filename stems are identical;
- exactly one component is a JPEG/HEIC/HEIF still; and
- exactly one component is a MOV motion file.

Unpaired stills and MOV files remain independent processable assets. If a stem
has a MOV plus multiple eligible stills, or one eligible still plus multiple
MOV files, no pair is formed and every candidate receives an
`ambiguous_live_photo_pair` warning.

A pair uses the still component as its primary metadata/timestamp record.
Duplicate comparison covers both component hashes. Canonical selection ranks
the total pair size, then the still timestamp-source preference, then the
component paths. Both canonical components are planned together. If either
target collides, both component actions are `collision`.

### Grouping and Planning Separation

Contextual grouping:

- is computed from the complete set of valid FileRecord objects
- is independent from duplicate grouping and canonical selection
- does not influence planner behavior

Planner:

- operates only on FileRecord and CorruptFile inputs
- is not affected by contextual grouping

Grouping and planning are parallel outputs of the pipeline.

---

## 10. Canonical Selection

Exactly one file per group is selected using:

1. largest size
2. prefer EXIF timestamp over `mtime`
3. lexicographically smallest path

For a Live Photo, “file” means the complete logical asset: combined component
size, still timestamp source, then the ordered component paths. Both components
of the selected asset are canonical.

---

## 11. Canonical Filename

``
YYYY-MM-DD_HHMMSS_<short-asset-hash>.<normalized-format-extension>
``

- JPEG normalizes to `.jpg`.
- TIFF normalizes to `.tif`.
- PNG, HEIC, HEIF, CR2, NEF, ARW, MP4 and MOV retain their supported extension.
- Live Photo components share the still timestamp and short asset hash, so
  their basenames match while their extensions remain distinct.

---

## 12. Target Path Resolution

### In-place

``
source.parent / filename
``

### Output mode

``
output/YYYY/MM/DD/filename
``

---

## 13. Action Classification

For canonical files:

- `skip`
- `collision`
- `rename`
- `move`

For duplicates:

- `duplicate`

---

## 14. Planner Output

Planner returns:

``
PlanResult:
    records
    actions
    corrupt_files
``

Rules:

- corrupt files do not produce records
- corrupt files do not produce actions
- corrupt files do not affect planning

---

## 15. Contextual Grouping

Contextual grouping:

- operates on `FileRecord` set
- produces `ContextualGrouping`
- independent from duplicate grouping
- does not affect planning

Grouping rule:

- records are ordered by:
  - timestamp (ascending)
  - path (lexicographically)
- consecutive records belong to the same group if:
  (current.timestamp - previous.timestamp) <= 300 seconds

- member references are relative POSIX-style paths
- group identifiers therefore do not depend on the absolute scan location

Included in output only when:

``
--context
``

---

## 16. Reporting

Output modes:

- console (default)
- JSON (`--json`)

Includes:

- summary
- records
- actions
- corrupt_files
- batch_contexts
- contextual_groups (optional)

Record metadata in JSON includes the selected timestamp candidate, every valid
candidate with naive/aware/UTC representations, camera/device context, keywords,
GPS, sidecar path, timezone basis, and clock correction.

Non-JPEG records also expose `media_format`. Paired Live Photo records expose
`live_photo_pair_id` and `live_photo_role` (`still` or `motion`). These additive
fields are omitted for ordinary JPEG records so the existing JPEG JSON contract
remains byte-for-byte stable.

JSON output:

- uses fixed indentation of 2 spaces
- object keys are serialized in lexicographic order

---

## 17. Apply Behavior

Default: dry-run

With `--apply`:

- execute actions for canonical files only
- duplicates are not modified
- corrupt files are not modified
- no overwrite allowed

---

## 18. Determinism

For identical input:

- identical scan results
- identical grouping
- identical planning
- identical output

No randomness allowed.

---

## 19. Constraints

- deterministic processing for the extensions in section 4.1
- exact duplicate detection only
- no perceptual hashing
- no file deletion
- no overwrite
- no concurrency
- no external state
- no implicit or explicit metadata rewriting
- no automatic GPS-based naming/grouping
- no hidden or prompt-only timestamp corrections
