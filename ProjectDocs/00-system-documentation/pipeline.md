# PhotoForge — Pipeline Orchestration

## Classification

CORE

## Purpose

`pipeline.py` composes a scanner snapshot, contextual grouping, and planning.
It does not define the behavior of those components.

## Entry point

`run_pipeline(input_path, *planner_args, plan_files=None,
build_contextual_grouping=None, scan_result=None, **planner_kwargs)` returns
`(PlanResult, ContextualGrouping)`.

## Execution flow

1. Resolve the injected or default planner.
2. Resolve the injected or default grouping builder.
3. Use the supplied `scan_result`; if it is `None`, call
   `scan_directory(input_path)` exactly once.
4. Read `records` from that snapshot.
5. Build contextual grouping exactly once.
6. Invoke the planner exactly once with the same records and forwarded
   arguments.
7. Return both results separately.

The CLI supplies its existing snapshot, producing a single-snapshot end-to-end
flow. Library callers may omit it and receive one pipeline-owned scan.

## Integration boundaries

The pipeline consumes only `ScanResult.records`. It does not derive corrupt
files, inspect diagnostics, alter planner arguments or results, embed grouping
in `PlanResult`, render output, or execute actions. Default planner loading is
from `.planner.plan_files`; grouping loading tries
`.grouping.build_contextual_grouping` then
`.contextual_grouping.build_contextual_grouping`. Missing integrations raise
`RuntimeError`.

## Invariants

Grouping precedes planning, both receive the identical immutable record tuple,
and each is called once. Injected dependencies and forwarded arguments remain
unchanged. No additional filesystem observation occurs when a snapshot is
supplied.
