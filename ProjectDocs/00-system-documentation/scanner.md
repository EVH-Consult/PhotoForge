# PhotoForge — Scanner Pipeline

## Purpose

The scanner pipeline is responsible for discovering filesystem entries under the input directory, filtering them deterministically, enriching processable files into complete `FileRecord` objects, and classifying files that cannot be fully processed.

The scanner does **not**:

- plan actions
- perform duplicate grouping
- perform contextual grouping
- generate filenames
- render reports
- modify the filesystem

The scanner returns a deterministic `ScanResult` containing:

- valid `FileRecord` objects
- skipped files
- scan issues
- deterministic counters

---

## Responsibility Boundary

### scanner.py is responsible for

- validating the input directory
- recursively discovering filesystem entries
- deterministic ordering of traversal results
- classifying entries by extension and file type
- reading file size and modification time
- invoking timestamp extraction
- invoking metadata normalization
- invoking SHA-256 hashing
- constructing `FileRecord`
- classifying corrupt files
- collecting skipped-file and issue diagnostics
- returning a deterministic `ScanResult`

### scanner.py is not responsible for

- converting corrupt scan results into `CorruptFile`
- planning rename or move actions
- duplicate grouping
- contextual grouping
- reporting or serialization
- applying filesystem changes

---

## High-Level Flow

For a given input directory, the scanner executes the following stages in order:

1. Validate input directory
2. Discover filesystem entries recursively
3. For each discovered path, classify:
   - symlink
   - non-regular file
   - unsupported extension
   - recognized but not processable format
   - processable format
4. For each processable file:
   - read file size and mtime
   - extract timestamp
   - normalize metadata
   - compute SHA-256
   - construct `FileRecord`
5. For failures during processable-file enrichment:
   - classify file as corrupt
   - record `SkippedFile`
   - record `ScanIssue`
6. Return a deterministic `ScanResult`

---

## Input Validation

Function:

    scan_directory(input_path: Path) -> ScanResult

Validation is performed by:

    _validate_input_directory(input_path: Path) -> Path

Rules:

- input path is normalized via `resolve(strict=True)`
- input path must exist
- input path must be accessible
- input path must be a directory

Failure behavior:

- if the path does not exist, raise `ValueError`
- if the path is inaccessible, raise `ValueError`
- if the path is not a directory, raise `ValueError`

These are fatal errors. Scanning does not continue.

---

## Discovery

Function:

    discover_files(input_path: Path) -> tuple[Path, ...]

Behavior:

- recursive traversal uses `os.walk(..., topdown=True, followlinks=False)`
- directory names are sorted lexicographically before descent
- filenames are sorted lexicographically before processing
- each discovered file path is converted to `Path(root) / filename`
- each discovered path is normalized with `resolve(strict=False)`

Output:

- deterministic tuple of discovered file paths

Notes:

- discovery collects filenames returned by `os.walk`
- symlink handling occurs later during per-path classification
- the scanner result counter `total_entries_seen` equals the number of discovered paths

---

## Extension Classification

The scanner distinguishes three extension classes.

### Processable extensions

Processable files are currently:

- `.jpg`
- `.jpeg`

Matching is case-insensitive.

These files continue through the enrichment pipeline.

### Recognized but not processable extensions

Recognized but not processable files are currently:

- `.png`
- `.heic`
- `.heif`
- `.cr2`
- `.nef`
- `.arw`
- `.mp4`
- `.mov`

Matching is case-insensitive.

These files are recognized by the scanner but are not processed into `FileRecord` objects.

They are recorded as:

- `SkippedFile(reason="recognized_not_processable")`

No issue is recorded for this classification.

### Unsupported extensions

Any extension not in the supported-extension set is treated as unsupported.

These files are recorded as:

- `SkippedFile(reason="unsupported_extension")`

No issue is recorded for this classification.

---

## Entry Classification Rules

For each discovered path, the scanner applies classification in this order.

### 1. Symbolic link

If `path.is_symlink()` is true:

- record `SkippedFile(reason="symlink")`
- do not process further

### 2. Non-regular file

If `path.is_file()` is false:

- record `SkippedFile(reason="not_regular_file")`
- do not process further

### 3. Unsupported extension

If `is_supported_file(path)` is false:

- record `SkippedFile(reason="unsupported_extension")`
- do not process further

### 4. Recognized but not processable format

If `is_recognized_file(path)` is true:

- record `SkippedFile(reason="recognized_not_processable")`
- do not process further

### 5. Processable file

Only files reaching this stage are enriched into `FileRecord`.

---

## Metadata Read Stage

Function:

    get_file_size_and_mtime(path: Path) -> tuple[int, float]

Returns:

- `size`: file size in bytes
- `mtime_timestamp`: modification time as POSIX timestamp

Failure behavior:

- `OSError` during metadata access causes corrupt-file classification

Corrupt classification:

- `SkippedFile.reason = "corrupt_metadata_unreadable"`
- `ScanIssue.severity = "error"`
- `ScanIssue.code = "corrupt_metadata_unreadable"`
- `ScanIssue.message = str(exception)`

No `FileRecord` is created for that file.

---

## Timestamp Extraction Stage

The scanner invokes timestamp extraction through:

    extract_timestamp(path: Path, mtime_timestamp: float) -> tuple[datetime, str]

This is provided by `exif.py`.

EXIF fallback order:

1. EXIF `DateTimeOriginal`
2. EXIF `DateTimeDigitized`
3. EXIF `DateTime`
4. filesystem `mtime`

Possible raw timestamp-source values returned by extraction:

- `exif_datetimeoriginal`
- `exif_datetimedigitized`
- `exif_datetime`
- `mtime`

Important behavior:

- missing EXIF is not an error
- unreadable or invalid EXIF inside `_read_exif(...)` falls back to empty EXIF data
- invalid EXIF datetime values are treated as missing and fallback continues
- `mtime` is a valid fallback result

After extraction, the scanner invokes metadata normalization:

    normalize_metadata(extracted_timestamp, extracted_timestamp_source)

The normalized result provides:

- `timestamp`
- `timestamp_source`

Failure behavior:

Any exception raised during extraction or normalization causes corrupt-file classification.

Corrupt classification:

- `SkippedFile.reason = "corrupt_timestamp_unresolved"`
- `ScanIssue.severity = "error"`
- `ScanIssue.code = "corrupt_timestamp_unresolved"`
- `ScanIssue.message = str(exception)`

No `FileRecord` is created for that file.

---

## Hashing Stage

The scanner computes content hashing through:

    compute_sha256(path: Path) -> str

Rules:

- algorithm is SHA-256
- full file content is hashed
- digest is lowercase hexadecimal
- full digest length is 64 characters

The scanner derives:

- `short_hash = sha256[:8]`

Failure behavior:

If hashing raises `OSError`:

- classify as `corrupt_file_unreadable`

If hashing raises any other exception:

- classify as `corrupt_hash_failed`

Corrupt classifications:

For unreadable file content:

- `SkippedFile.reason = "corrupt_file_unreadable"`
- `ScanIssue.severity = "error"`
- `ScanIssue.code = "corrupt_file_unreadable"`
- `ScanIssue.message = str(exception)`

For other hashing failure:

- `SkippedFile.reason = "corrupt_hash_failed"`
- `ScanIssue.severity = "error"`
- `ScanIssue.code = "corrupt_hash_failed"`
- `ScanIssue.message = str(exception)`

No `FileRecord` is created for that file.

---

## FileRecord Construction

A `FileRecord` is created only if all enrichment stages succeed.

Definition:

    @dataclass(frozen=True)
    class FileRecord:
        path: Path
        size: int
        timestamp: datetime
        timestamp_source: str
        sha256: str
        short_hash: str

Field population:

- `path` = discovered file path
- `size` = metadata size
- `timestamp` = normalized metadata timestamp
- `timestamp_source` = normalized metadata timestamp source
- `sha256` = full SHA-256 digest
- `short_hash` = first 8 characters of `sha256`

Rules:

- no partial `FileRecord` objects are allowed
- a file either becomes one complete `FileRecord` or it is skipped/classified as corrupt

---

## Corrupt File Classification

A file is classified as corrupt if it is processable by extension but cannot be fully enriched into a valid `FileRecord`.

Corrupt reason values currently used by the scanner:

- `corrupt_metadata_unreadable`
- `corrupt_timestamp_unresolved`
- `corrupt_file_unreadable`
- `corrupt_hash_failed`

Rules:

- corrupt classification is deterministic
- corrupt files do not produce `FileRecord`
- corrupt files are represented inside `ScanResult` through:
  - `SkippedFile.reason`
  - `ScanIssue.code`
- scanner does not construct `CorruptFile`

---

## Diagnostic Structures

### SkippedFile

Definition:

    @dataclass(frozen=True)
    class SkippedFile:
        path: Path
        reason: str

Reason values currently emitted by the scanner:

Non-corrupt reasons:

- `symlink`
- `not_regular_file`
- `unsupported_extension`
- `recognized_not_processable`

Corrupt reasons:

- `corrupt_metadata_unreadable`
- `corrupt_timestamp_unresolved`
- `corrupt_file_unreadable`
- `corrupt_hash_failed`

### ScanIssue

Definition:

    @dataclass(frozen=True)
    class ScanIssue:
        path: Path
        severity: str
        code: str
        message: str

Current scanner behavior:

- corrupt-file classifications produce `ScanIssue` with `severity="error"`
- non-corrupt skips do not produce `ScanIssue`

Important boundary:

- `ScanIssue` is diagnostic only
- downstream corrupt-file propagation does not derive from `ScanIssue`
- the runtime transformation to `CorruptFile` is based on `SkippedFile.reason` values with the `corrupt_` prefix

---

## Scan Result

Definition:

    @dataclass(frozen=True)
    class ScanResult:
        records: tuple[FileRecord, ...]
        skipped: tuple[SkippedFile, ...]
        issues: tuple[ScanIssue, ...]
        total_entries_seen: int
        supported_files_processed: int

Meaning:

- `records` contains all successfully enriched valid files
- `skipped` contains all deterministic skip classifications
- `issues` contains recorded error diagnostics
- `total_entries_seen` equals number of discovered paths
- `supported_files_processed` equals number of created `FileRecord` objects

Current implementation behavior:

- `supported_files_processed = len(records)`

---

## Ordering Rules

The scanner enforces explicit ordering.

### Discovery ordering

- directory names sorted lexicographically
- filenames sorted lexicographically
- discovered output reflects deterministic walk order

### Returned collections

Before `ScanResult` is returned:

- `records` preserve deterministic processing order from discovered paths
- `skipped` are sorted lexicographically by `path`
- `issues` are sorted by:
  - `path`
  - then `code`

No implicit ordering is relied upon.

---

## Determinism Guarantees

For identical input and filesystem state, the scanner must produce identical:

- discovered path ordering
- skip classification
- corrupt classification
- `FileRecord` values
- `SkippedFile` values
- `ScanIssue` values
- `ScanResult` counters

Scanner behavior must not depend on:

- randomness
- environment variables
- locale-dependent parsing
- filesystem traversal nondeterminism

---

## Integration Boundary

The scanner returns `ScanResult` only.

The scanner does not convert scan output into planner-layer corrupt-file structures.

Current runtime integration is:

1. scanner returns `ScanResult`
2. CLI derives `CorruptFile` objects from `scan_result.skipped`
3. derivation rule is:
   - include entries where `SkippedFile.reason` starts with `"corrupt_"`
   - map:
     - `CorruptFile.path = SkippedFile.path`
     - `CorruptFile.error_type = SkippedFile.reason`
4. `ScanIssue` is not used for this transformation

This transformation is outside the scanner boundary.

---

## Final Contract

`scan_directory(input_path)` must:

1. validate the input directory
2. discover entries recursively in deterministic order
3. classify each discovered path deterministically
4. enrich processable JPEG files into complete `FileRecord`
5. classify per-file enrichment failures as corrupt
6. collect skipped-file and issue diagnostics
7. return deterministic `ScanResult`

The scanner produces complete valid records and deterministic diagnostics only.

It does not plan, report, group, or execute.
