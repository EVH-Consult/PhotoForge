# Filename Timestamp Extractor — INTERNAL

`extract_filename_timestamp(filename)` returns zero or one
`TimestampCandidate`. It searches left-to-right using ordered patterns for
`YYYYMMDD_HHMMSS`, dashed datetime variants, compact dates, and dashed dates.
At the same position, full datetime patterns precede date-only patterns.
Invalid calendar values are skipped. Full values have `datetime` precision;
date-only values use midnight and `date` precision. The extractor assigns
source kind `filename`, never infers a timezone, and does not resolve
cross-source precedence.
