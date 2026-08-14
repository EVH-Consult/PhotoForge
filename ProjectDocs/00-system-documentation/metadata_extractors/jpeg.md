# JPEG Timestamp Extractor — INTERNAL

`extract_jpeg_timestamp(path, mtime_timestamp)` concatenates EXIF timestamp
candidates followed by the filesystem modification-time candidate. It preserves
the order and values returned by those extractors and performs no validation,
precedence resolution, normalization, or diagnostics processing.
