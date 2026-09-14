# Repository: <https://github.com/EVH-Consult/PhotoForge>

## Repository Access

The repository URL is an authorized source.

You MUST:

- fetch required files from the repository when needed;
- not wait for manual upload if files are accessible via the repository;
- treat the repository as available implementation input.

Do not block execution solely because files were not uploaded if they are available in the repository.

---

You are working on the PhotoForge project.

---

## Mandatory Rule Sources

Load and apply:

- `ProjectDocs/ChatGPT-rules.md`
- `ProjectDocs/README.md`

Repository-local rules apply to implementation/documentation work, but they do not override EVH Consult Jira lifecycle or Confluence source-of-truth governance.

---

## Source-of-truth boundaries

### Work state

Use EVH Consult Jira (`EVHC`) for current backlog, work selection, dependencies, acceptance criteria, assignee, lifecycle state, review and completion evidence.

Do **not** use `ProjectDocs/01-backlog/backlog.md`, planning proposals, scope approvals or milestone files as the current work queue or current workflow state. Those files are retained repository history/version-cycle evidence unless a current Jira item explicitly requires one as an implementation artifact.

### Behaviour and implementation

Use the current repository implementation, tests and `SPEC.md` as the behavioural/implementation truth. Historical specifications are not authoritative.

### Durable architecture and decisions

Use the EVH Consult Confluence PhotoForge area for durable architecture rationale, system boundaries, significant decisions and source-of-truth ownership. Do not recreate that material in this prompt.

---

## Required Sources

Load only the sources needed for the current Jira task.

Typical repository sources include:

- `ProjectDocs/ChatGPT-rules.md`
- `ProjectDocs/README.md`
- `SPEC.md`
- `README.md`
- relevant files under `ProjectDocs/00-system-documentation/`
- relevant source and tests under `src/` and `tests/`
- relevant release/version evidence under `ProjectDocs/09-version-documentation/`

Historical planning or milestone files may be read when provenance is needed, but must not be treated as current work state.

Do not rely on memory when an authoritative connected source is available.

---

## Architecture

Do not embed a second fixed architecture summary here. Load the current code, `SPEC.md` and relevant system documentation for the task. If durable rationale is required, consult the canonical Confluence PhotoForge architecture/decision pages.

---

## Interaction and output

Follow `ProjectDocs/ChatGPT-rules.md` for repository-specific implementation discipline and formatting where applicable.

Before implementation, establish from Jira:

1. current work item and scope;
2. current lifecycle state and assignee;
3. dependencies/blockers;
4. acceptance criteria and review expectations.

Then load only the repository and Confluence sources needed to execute that Jira scope.
