# Folder Timestamp Extractor — INTERNAL

`extract_folder_timestamp(folder_name)` returns zero or one folder
`TimestampCandidate`. Matches are ordered by position and then pattern
priority, with supported ranges before supported single dates. For ranges, the
start date is returned. Invalid calendar values are skipped. Returned values
use midnight, `date` precision, source kind `folder`, and no timezone. The
caller selects which folder name to inspect; this module performs no traversal
or cross-source resolution.
