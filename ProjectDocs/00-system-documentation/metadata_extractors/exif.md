# EXIF Metadata Extractor — INTERNAL

`extract_exif_metadata(path)` loads image EXIF through Pillow and returns
timestamp candidates plus extraction diagnostics. Timestamp tags are inspected
in the fixed order DateTimeOriginal, DateTimeDigitized, then DateTime; each tag
is paired only with its corresponding offset tag. Valid timestamps use
`YYYY:MM:DD HH:MM:SS`. Offsets require signed `HH:MM` syntax with bounded
hours and minutes.

Missing EXIF yields a `missing` diagnostic. Image/EXIF read failure yields
`unreadable`. Invalid timestamp or offset fields yield deterministic
field-specific `invalid` diagnostics; an invalid offset does not discard its
valid timestamp. The module returns all valid EXIF candidates in tag order and
does not resolve precedence. The two public convenience functions return only
candidates or only diagnostics from the same extraction behavior.

`extract_exif_context(path)` separately exposes trimmed camera make/model,
Windows XPKeywords, and paired GPS latitude/longitude. Invalid or unreadable
context returns empty fields and never changes timestamp fallback. The scanner
merges this read-only context with XMP context using EXIF as the GPS preference.
