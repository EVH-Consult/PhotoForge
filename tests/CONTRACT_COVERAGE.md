# Regression map

`SPEC.md` is the behavioral authority. This map explains risk-based coverage;
it is not a second specification or a percentage target.

| Contract surface | Existing coverage | Added regression coverage |
| --- | --- | --- |
| Single scan, canonical selection, reserved targets | `test_core_determinism.py` | canonical ranking under every input permutation; existing target and duplicate non-actions |
| Full-content SHA-256 and corrupt propagation | media and E2E tests | empty, exact chunk boundary and multi-chunk hashes; controlled I/O and generic hashing failures |
| Timestamp provenance and correction | extractor, resolution, policy and diagnostics modules | retained unchanged; general coverage does not redefine timestamp behavior |
| Contextual grouping is deterministic and presentation-only | E2E context/determinism | inclusive 300-second boundary, chained adjacency, reversed input; default/context plan equality |
| CLI dry-run and validation | E2E baseline | mutation sentinel, source-byte preservation and invalid-input pre-scan rejection |
| Format preservation and complete Live Photo assets | `test_media_formats_and_live_photos.py` | retained existing format matrix, duplicate pairs and pair-wide collision tests |
| Stable reporting | reporter and E2E golden modules | retained byte-for-byte golden oracles |

No coverage dependency or numeric threshold is introduced. The existing
Python 3.10/3.12, Ubuntu/Windows CI matrix executes these tests with pytest.
Real permission failures are injected rather than relying on OS permissions or
the test runner's privileges. Personal media and external services are excluded.
Future performance, naming and CLI features carry their own acceptance tests.
Filesystem mutation execution is outside this test-only change; the CLI safety
test fails if the default path invokes the application seam.
