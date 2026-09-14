# PhotoForge documentation ownership

This directory contains repository-local technical and historical documentation for PhotoForge. It is not the authoritative work tracker for EVH Consult.

## Canonical sources

### GitHub repository

The `EVH-Consult/PhotoForge` repository owns versioned implementation truth, including:

- source code and tests;
- `SPEC.md`, the current behavioural contract;
- the public `README.md`;
- code-adjacent architecture and module documentation under `ProjectDocs/00-system-documentation/`;
- build, development, validation, release and contributor documentation that must evolve with the implementation;
- historical specifications and version-cycle artifacts, when retained as version history.

Historical specifications such as `SPEC_v0.x.md` are evidence of earlier versions only. They are not current behavioural authority.

### Jira

The EVH Consult Jira project (`EVHC`) owns finite work and its lifecycle, including:

- backlog and work selection;
- implementation tasks and defects;
- acceptance criteria;
- dependencies;
- assignee/active ownership;
- workflow status, review and completion evidence.

`ProjectDocs/01-backlog/` and the version-planning, scope-approval and milestone files under `ProjectDocs/` are retained as legacy/historical version-cycle artifacts. They must not be used as a competing current backlog or as evidence of current Jira work state.

New or still-relevant future work belongs in Jira rather than being added to the repository backlog. Historical entries are not automatically current Jira commitments.

### Confluence

The EVH Consult Confluence PhotoForge area owns durable project knowledge that should outlive an implementation revision, including:

- architectural rationale and system boundaries;
- major cross-cutting design decisions and trade-offs;
- project-level operating context and source-of-truth boundaries.

Confluence must not duplicate `SPEC.md` or redefine current runtime behaviour. It should point back to the repository for behavioural and implementation truth.

Relevant canonical pages:

- PhotoForge
- PhotoForge Architecture
- PhotoForge Decision Log

## Legacy version workflow material

`ProjectDocs/development-workflow.md`, the numbered planning folders, templates and completed version artifacts document the repository's earlier deterministic version-cycle process. They remain useful as implementation history and as a reference for versioned technical/release artifacts, but they do not supersede the current EVH Consult Jira lifecycle.

Where old repository documents refer to `ProjectDocs/01-backlog/backlog.md`, planning proposals, scope approvals or milestone files as the active work state, interpret those references historically. Current work state must be read from Jira.

## Rule of thumb

- Need to know what PhotoForge **does now**? Read code, tests and `SPEC.md`.
- Need repository-local implementation or release detail? Read the relevant GitHub documentation.
- Need to know **what work is planned, active, blocked, under review or done**? Read Jira.
- Need durable architecture rationale or significant decisions? Read Confluence.
