# `timestamp_policy`

## Classification

CORE

## Purpose

Load and apply explicit deterministic timestamp correction/inference rules.

## Contract

The UTF-8 JSON policy must contain `"version": 1`. It can define a default,
exact input-relative folder rules, exact camera make/model rules, and named GPS
rectangles. Offsets use signed `+HH:MM`/`-HH:MM` values.

Clock corrections change non-filesystem wall-clock candidates. Filesystem mtime
is already UTC and is excluded from correction and timezone inference. For all
other candidates, timezone choice is ordered: folder rule, device rule, embedded
offset, configured GPS rectangle, trusted-device consensus, default. Overlapping
GPS rules are accepted only when their offsets agree.

Folder and device rules compose independently for `timezone_offset` and
`clock_correction`: an omitted field falls through to the next matching rule
rather than selecting one rule object as a whole.

## Determinism and safety

Rules are matched exactly; configuration order does not change folder/device
selection. No network, operating-system local timezone, prompt state, or metadata
write participates in policy application.
