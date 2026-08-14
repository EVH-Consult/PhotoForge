# Timestamp Resolution — INTERNAL

`resolve_timestamp_candidates` filters candidates with
`is_valid_timestamp_candidate`, applies source precedence
EXIF → filename → folder → filesystem, preserves input order within a source,
and returns the first candidate plus the complete sorted valid tuple. It raises
`ValueError` when no valid candidate remains or when an otherwise valid
candidate has an unsupported source kind.

Current validity requires `datetime` precision, a naive stored datetime, a
supported source kind, and either no offset or an offset accepted by
`datetime.timezone`. Date-precision filename and folder candidates are
therefore extracted but are not currently eligible for resolution.
