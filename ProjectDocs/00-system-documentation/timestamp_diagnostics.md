# Timestamp Diagnostics — INTERNAL

`build_metadata_diagnostics` deterministically sorts valid candidates and
extraction diagnostics, compares every pair with different source details, and
records unequal comparable pairs as inconsistencies. Candidates are comparable
only when both use the same representation: UTC when each has an offset, or
naive when neither has one. Mixed representations are ignored. Aware candidates
are converted to UTC only for comparison. Diagnostics never alter timestamp
selection or pipeline behavior.
