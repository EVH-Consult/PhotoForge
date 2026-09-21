# PhotoForge — TIFF Metadata Extractor

## Classification

INTERNAL

## Purpose

`extract_tiff_timestamp` returns readable EXIF timestamp candidates followed by
the deterministic filesystem `mtime` candidate. It performs no normalization,
cross-source resolution, format validation, or filesystem mutation.
