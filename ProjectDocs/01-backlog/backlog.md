# PhotoForge Backlog — historical legacy list

> **Current work tracking:** EVH Consult Jira (`EVHC`) is authoritative for PhotoForge backlog, work selection, dependencies, acceptance criteria and lifecycle state. This file is retained as historical repository evidence from the earlier PhotoForge version-cycle workflow. Do not add new active work here and do not infer current commitments or Jira status from these entries. See `ProjectDocs/README.md` for the current source-of-truth model.

This file historically tracked ideas, improvements, and future work.

Nothing in this file should be treated as current selected scope unless represented by a current Jira work item.

Historical backlog hygiene rules were:

- Keep entries minimal and one-line
- Prefer extending existing entries over creating new ones
- Avoid duplication across sections
- Do not include implementation details or solutions

---

## Timestamp & EXIF

- Handle incorrect camera timezone (manual offset)
- Per-folder or per-batch timezone correction
- Support GPS-based timezone inference
- Detect inconsistent timestamp clusters
- Optional interactive timestamp correction
- Support EXIF timezone fields if present
- Use filename patterns as fallback timestamp source when EXIF is missing
- Use folder name patterns as fallback timestamp source when EXIF is missing
- Classify timestamp inconsistencies as comparable vs non-comparable
- Infer timezone correction from trusted device clusters
- Detect event-bounded folders vs mixed-content folders

---

## File Format Support

- Full processing support for non-JPEG formats
- TIFF support
- Define TIFF metadata extraction completeness
- Apple Live Photos handling

---

## Duplicate Handling

- Optional duplicate deletion
- Duplicate reporting enhancements
- Perceptual hashing (near-duplicate detection)
- Configurable canonical selection rules (beyond timestamp, size, filename patterns, source preference)
- Prefer original filenames over copy variants (e.g. “- Copy”, “(1)”)
- Detect same-photo-different-encoding cases

---

## Naming & Organization

- Custom filename templates
- Folder-by-camera model
- Folder-by-event or grouping
- User-defined filename rules
- User-defined folder structure rules
- Support additional filename timestamp patterns

---

## Performance

- Parallel hashing
- Incremental scanning (cache results)
- Large library optimization
- I/O performance improvements
- Size-based pre-grouping before hashing

---

## CLI & UX

- Verbosity levels
- Progress indicator
- Dry-run diff-style output
- Interactive confirmation mode
- Better error reporting formatting
- Improve console output usability for large scans

---

## Metadata

- Sidecar (XMP) support
- Metadata rewriting
- Keyword/tag extraction
- GPS-based naming or grouping
- Extract metadata from filenames
- Extract metadata from folder names
- Infer batch context from metadata sources
- Expose EXIF diagnostics (missing, unreadable, invalid fields)
- Define metadata source trust model
- Expose structured timestamp representations in output

---

## Advanced Features

- Face detection
- Event clustering
- AI-based photo classification
- Quality scoring / best photo selection

---

## Integration

- iCloud Photos integration
- Google Photos integration
- Dropbox / OneDrive support
- Watch mode (auto-process new files)
- Apple Live Photos handling

---

## Project / Dev

- PyPI packaging and publishing
- GitHub Actions (CI)
- Test coverage expansion
- Documentation for contributors
- Add a scripted procedure to export and flatten project files for ChatGPT source uploads
- Deterministically rename exported files to preserve scope in flat source contexts
- Include docs, templates, specs, and source modules in the export bundle
- Refresh ChatGPT source bundle after each validated milestone commit or release
- Replace version.py by pyproject.toml
- Define and enforce runtime pyproject.toml
- Move CHANGELOG.md to /
- Align EXIF module placement with metadata_extractors structure
- Formalize scope-refinement-addendum as part of scope approval workflow
- Define scope-refinement-template.md
- Define rules for creation, content, and validation of scope-refinement-addendum
- Define storage and lifecycle rules for scope-refinement-addendum
- Define requirements-template.md
- Improve release-checklist-template.md
- Resolve inconsistency between release checklist creation step and storage location in development-workflow.md
- Convert milestone checklist template validation items to checkbox format
- Define formal checkbox semantics for milestone checklist validation states
- Reduce milestone checklist boilerplate without weakening determinism or auditability

---

## Historical notes

- v0.1 scope was intentionally minimal and deterministic.
- Items in this historical list were out of v0.1 scope unless explicitly promoted under the earlier workflow.
- A still-useful item must now be represented and selected through Jira before it is treated as current work.
