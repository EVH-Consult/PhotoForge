# Contributing to PhotoForge

Start with [README.md](README.md) and the current [SPEC.md](SPEC.md).
The specification is the behavioral contract; historical `SPEC_v0.x.md` files
are version history. Change the contract, implementation and regression tests
together when proposing behavior changes.

## Set up a development environment

Use Python 3.10 or newer. CI currently tests Python 3.10 and 3.12 on Ubuntu
and Windows. From a checkout of this repository:

```sh
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on a POSIX shell or
`.venv\Scripts\Activate.ps1` in Windows PowerShell. Then run:

```sh
python -m pip install -r requirements.txt
python -m pip install -e .
python -m photoforge.cli --help
python -m pytest -q
```

`requirements.txt` contains the development/test pins; `pyproject.toml`
defines package metadata, runtime dependencies and the console entrypoint.
Editable installation makes source changes visible locally. The installed
`photoforge` command and `python -m photoforge.cli` expose the same CLI boundary.
CI installs the requirements, installs the package with `python -m pip install .`,
then runs `python -m pytest -q`. A checkout install is the supported path here;
these instructions do not claim a published PyPI release.

## Find the relevant code and tests

- `src/photoforge/scanner.py`: discovery, metadata orchestration and scan results.
- `metadata_extractors/`, timestamp modules: extraction, provenance and policy.
- `hashing.py`, `grouping.py`, `planner.py`: exact hashing, structural groups and plans.
- `naming.py`: explicit naming configuration and portable templates.
- `cli.py`, `cli_reporting.py`, `reporter.py`: CLI boundary and presentation.
- `operations.py`: explicit application of planned filesystem operations.
- `tests/`: focused unit/integration tests; `tests/e2e/`: synthetic fixtures,
  manifests, golden reports and deterministic repeat-run checks.

For a focused edit, run its relevant module, then the complete suite:

```sh
python -m pytest -q tests/test_naming_rules.py
python -m pytest -q tests/test_cli_usability.py
python -m pytest -q
python scripts/verify_e2e_golden.py --all
git diff --check
```

The golden verifier compares existing expected output; do not regenerate goldens
merely to make a failure disappear. For an intentional accepted contract change,
inspect the generator's help (`python scripts/generate_e2e_golden.py --help`),
regenerate the affected fixture only, and review every changed expected output.
Synthetic fixture provenance is described in
[the fixture README](tests/e2e/fixtures/demo/README.md) and verified by the suite.

For performance changes, run the diagnostic benchmark:

```sh
python scripts/benchmark_scanning.py
```

It creates temporary synthetic libraries, compares complete serial/parallel
scan/plan/report results and prints timings plus peak Python allocations.
Storage and machine differences affect timings; they are not CI thresholds.
See SPEC.md for snapshot and rescan requirements. Run test commands from the
repository root; shell activation and executable names may vary by platform.

## Preserve safety and determinism

Use generated synthetic media and controlled failures, never personal/customer
photos, real location metadata, credentials or secrets. Review default dry-run
output before considering explicit filesystem mutation. Test application
boundaries with mocks or isolated disposable fixtures; never apply a plan to
an irreplaceable library while developing.

Tests should check observable contracts: stable ordering, full-content duplicate
evidence, timestamp provenance, collision behavior, paired Live Photo integrity,
JSON stream stability and opt-in interaction. Avoid wall-clock assertions,
uncontrolled filesystem permissions, machine-specific paths and arbitrary
coverage percentages. New behavior needs focused regressions; unchanged goldens
provide a compatibility oracle. Keep new dependencies justified and compatible
with the supported Python/OS matrix.

## Propose a change

Keep branches, commits and pull requests narrowly scoped. Describe the concrete
problem, resulting behavior, any specification changes, tests run and known
limitations. Review the diff for unrelated/generated/sensitive files. Make CI
pass and obtain the appropriate independent technical review before an authorized
merge. Implementation self-checks do not replace acceptance.

External contributors can use GitHub issues and PR discussions; access to private
EVH Consult systems is not a prerequisite. Maintainers reconcile accepted work
with Jira, which owns selection, dependencies, ownership, review and completion.
Do not recreate an active backlog or milestone lifecycle in `ProjectDocs`.

The [documentation ownership guide](ProjectDocs/README.md) defines the boundaries:
Git owns versioned code, tests, SPEC and contributor/build instructions; Jira
owns finite work and lifecycle evidence; Confluence owns durable architecture,
decisions and rationale. Historical planning/templates remain historical.
Keep routine work status out of durable architecture documents. A merge, passing
CI or a local test is evidence of its own result, not automatic Jira acceptance.
