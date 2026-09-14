# Development Workflow — historical legacy process

> **Historical status:** This document no longer defines the current PhotoForge work lifecycle. EVH Consult Jira (`EVHC`) is authoritative for backlog, selected scope, dependencies, acceptance criteria, assignee, lifecycle state, review and completion evidence. See `ProjectDocs/README.md` for the current source-of-truth model.
>
> The repository-managed version-cycle workflow formerly stored in this file is preserved in Git history, including the EVHC-24 branch state at commit `83daa12f018edc42100302dd34005143d9ee09c1`. Its backlog, scope-approval, milestone, transition and enforcement rules are historical process evidence only and must not be interpreted as current Jira state or current EVH Consult lifecycle governance.

## Current use

This file remains as an explicit compatibility entry point for older repository references to `ProjectDocs/development-workflow.md`.

For current PhotoForge work:

- use Jira (`EVHC`) for backlog, work selection, scope, dependencies, acceptance criteria, ownership, workflow state, review and completion;
- use the repository implementation, tests and `SPEC.md` for current behavioural and implementation truth;
- use the EVH Consult Confluence PhotoForge area for durable architecture rationale, system boundaries and significant decisions;
- use historical planning, scope, requirements, milestone and release-cycle files only as provenance unless a current Jira item explicitly incorporates one as an implementation artifact.

## Historical workflow provenance

The previous contents of this file described the earlier deterministic repository version-cycle process from backlog maintenance through version scope, requirements, milestones, validation, release and next-cycle planning.

Those historical rules remain available through Git version history. Statements in earlier revisions such as “mandatory,” “authoritative,” “current workflow,” fixed transition sequences, or requirements to derive scope from `ProjectDocs/01-backlog/backlog.md` describe that former repository process in its original context. They do not override:

1. current EVH Consult source-of-truth governance;
2. the live Jira lifecycle and current EVHC work item;
3. `ProjectDocs/README.md` ownership boundaries;
4. current repository implementation and `SPEC.md` for behaviour.

No active PhotoForge work should be created, selected, transitioned or completed through the historical workflow described by earlier revisions of this file.
