# `metadata_extractors.xmp`

## Classification

INTERNAL

## Purpose

Read an optional same-stem `.xmp`/`.XMP` sidecar without modifying it.

## Behaviour

- Sidecar selection is deterministic by filename order.
- XML parse/read failures return an `xmp/unreadable` diagnostic.
- Timestamp fields are read in `CreateDate`, `DateCreated`, `ModifyDate` order.
- ISO-8601 timezone offsets are retained on `TimestampCandidate`.
- RDF list values are normalized into a unique, case-stably sorted keyword tuple.
- Decimal GPS latitude/longitude values with optional compass suffixes are exposed
  only when both coordinates are valid.

## Boundary

The module does not select a primary timestamp, infer a timezone, change naming
or grouping, or write XMP/media metadata.
