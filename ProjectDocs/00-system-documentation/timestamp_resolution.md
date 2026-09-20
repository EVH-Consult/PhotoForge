# Timestamp Resolution — INTERNAL

`resolve_timestamp_candidates` filters candidates with
`is_valid_timestamp_candidate`, applies source precedence
EXIF → XMP → filename → folder → filesystem, preserves input order within a source,
and returns the first candidate plus the complete sorted valid tuple. It raises
`ValueError` when no valid candidate remains or when an otherwise valid
candidate has an unsupported source kind.

Current validity accepts `date` and `datetime` precision, requires a naive stored
datetime and a supported source kind, and requires any provided offset to be
accepted by `datetime.timezone`. Date-precision candidates represent midnight.
