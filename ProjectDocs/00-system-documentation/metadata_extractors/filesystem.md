# Filesystem Timestamp Extractor — INTERNAL

`extract_filesystem_timestamp_candidates(path, mtime_timestamp)` converts the
provided modification-time value through UTC and removes timezone information
from the stored candidate. It returns one `datetime`-precision candidate with
source kind `filesystem` and detail `filesystem_mtime`, or an empty tuple
when conversion is invalid or outside the platform range. The path is currently
accepted for the extractor contract but does not affect the result.
