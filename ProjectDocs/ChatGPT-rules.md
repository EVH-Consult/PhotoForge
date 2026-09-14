# ChatGPT Rules — PhotoForge

This document defines repository-specific interaction rules for ChatGPT when working on PhotoForge implementation and repository documentation.

These rules ensure deterministic, high-quality, implementation-safe outputs. Source-of-truth ownership is defined in `ProjectDocs/README.md` and must be applied together with these rules.

---

## 1. Formatting Rules (CRITICAL)

- Responses must be copy-paste safe by default.
- Nested fenced code blocks should be properly nested to avoid rendering issues.
- Markdown must not break rendering in common clients (VSCode, GitHub, ChatGPT UI).
- When generating `.md` documents:
  - output must be contained in a single fenced code block when the user explicitly needs copy-paste document text;
  - no additional fences may break the outer formatting.
- Inline code blocks must not interfere with outer formatting.

---

## 2. No Guessing Rule (HARD CONSTRAINT)

ChatGPT must not:

- guess behavior;
- infer undocumented logic;
- assume missing implementation details;
- “fill in” unspecified behavior.

If information is missing, load the relevant connected authoritative source where available. Ask for input only when the required source cannot be accessed or the decision genuinely belongs to the user.

---

## 3. Source-of-Truth Hierarchy

Apply `ProjectDocs/README.md` for the full ownership model.

For repository behavior and implementation:

1. current implementation and tests are authoritative for what the code actually does;
2. `SPEC.md` is the current behavioural contract and must remain aligned with implementation;
3. repository-local system documentation must reflect implementation;
4. historical specs and version-cycle artifacts are evidence only unless a current Jira item explicitly requires them as implementation inputs.

For work management:

- EVH Consult Jira (`EVHC`) is authoritative for backlog, selected scope, dependencies, acceptance criteria, assignee, lifecycle state, review and completion evidence;
- `ProjectDocs/01-backlog/`, planning proposals, scope approvals and milestone files must not be treated as a competing current work tracker.

For durable architecture and significant decisions:

- use the EVH Consult Confluence PhotoForge area;
- do not duplicate durable rationale into repository prompts or specifications when a link/reference is sufficient.

---

## 4. Determinism Enforcement

All implementation outputs must respect the current documented deterministic contract, including explicit ordering and absence of hidden/random behavior where determinism is required.

ChatGPT must:

- call out implicit ordering that could affect behavior;
- reject ambiguous behavioral definitions;
- keep documentation wording consistent with the implemented/specification contract.

---

## 5. Scope Discipline

ChatGPT must:

- operate strictly within the current Jira work-item scope and acceptance criteria;
- respect current dependencies and lifecycle state;
- not introduce redesign;
- not introduce unrelated features;
- not expand scope implicitly.

Historical milestone/scope files may provide provenance but do not define current selected work unless the current Jira item explicitly incorporates them.

If a gap is identified:

- flag it explicitly;
- do not silently resolve it outside scope;
- create or recommend separate Jira work when the gap is real and finite.

---

## 6. Documentation Rules

When generating or validating repository documentation:

- behavior documentation must describe the system as implemented/currently specified, not merely as originally designed;
- durable architectural rationale belongs in Confluence rather than being copied into multiple repository documents;
- current work status belongs in Jira rather than repository prose.

Repository documents must be:

- consistent with implementation where they describe implementation;
- consistent with `SPEC.md` where they describe behavioral contracts;
- free of contradictions and stale authority claims.

---

## 7. Validation Behavior

When validating:

- focus on real mismatches between code, tests, `SPEC.md`, repository documentation and the applicable Confluence/Jira authority;
- ignore stylistic preferences unless they introduce ambiguity;
- clearly classify material issues.

ChatGPT must:

- provide actionable corrections;
- not rewrite everything unnecessarily;
- not introduce speculative fixes.

---

## 8. Interaction Rules

ChatGPT must:

- be direct and precise;
- avoid filler or generic explanations;
- avoid unnecessary verbosity.

ChatGPT must not:

- patronize;
- over-explain obvious concepts;
- derail into unrelated topics.

---

## 9. Output Discipline

- Outputs must be immediately usable.
- No placeholder leakage unless explicitly required by a template.
- No broken formatting.
- Do not present historical repository planning artifacts as current Jira state.

---

## 10. Priority of Rules

If repository-local rules conflict:

1. current EVH Consult source-of-truth and Jira lifecycle governance;
2. no-guessing / authoritative-source verification;
3. current implementation and `SPEC.md` for behavior;
4. determinism requirements;
5. current Jira scope discipline;
6. formatting/output preferences.

---

## 11. Enforcement

If a rule is violated:

- acknowledge the concrete violation;
- correct the durable source or active work state where appropriate;
- continue from the corrected authoritative state rather than preserving a known contradiction.
