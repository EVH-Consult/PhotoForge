from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias, cast

from .model import ContextualGrouping, FileRecord, PlanResult
from .scanner import ScanResult, scan_directory

PlannerFunction: TypeAlias = Callable[..., PlanResult]
GroupingBuilder: TypeAlias = Callable[[tuple[FileRecord, ...]], ContextualGrouping]


def run_pipeline(
    input_path: Path,
    *planner_args: object,
    plan_files: PlannerFunction | None = None,
    build_contextual_grouping: GroupingBuilder | None = None,
    scan_result: ScanResult | None = None,
    **planner_kwargs: object,
) -> tuple[PlanResult, ContextualGrouping]:
    """Run the composed pipeline without changing existing planner behavior.

    This orchestration function is the sole integration point for contextual
    grouping. It composes scanning, planning, and contextual grouping while
    keeping each responsibility in its existing module.

    Rules enforced by this function:
    - scanning is delegated to scanner.scan_directory(...)
    - planning is delegated to the existing planner entry point unchanged
    - contextual grouping is computed exactly once from the complete valid
      ``tuple[FileRecord, ...]`` returned by the scanner
    - the resulting ``ContextualGrouping`` is returned separately and is not
      embedded into existing pipeline models

    ``planner_args`` and ``planner_kwargs`` are forwarded directly to the
    planner entry point so the existing planning interface can remain unchanged.
    """

    planner = plan_files if plan_files is not None else _load_plan_files()
    grouping_builder = (
        build_contextual_grouping
        if build_contextual_grouping is not None
        else _load_grouping_builder()
    )

    effective_scan_result = scan_result or scan_directory(input_path)
    records = effective_scan_result.records

    grouping = grouping_builder(records)
    plan_result = planner(records, *planner_args, **planner_kwargs)

    return plan_result, grouping


def _load_plan_files() -> PlannerFunction:
    try:
        from .planner import plan_files
    except ImportError as exc:  # pragma: no cover - depends on integration state
        raise RuntimeError(
            "Unable to import planner entry point '.planner.plan_files'. "
            "Pass plan_files=... explicitly or complete planner integration."
        ) from exc

    return plan_files


def _load_grouping_builder() -> GroupingBuilder:
    module_candidates = (
        (".grouping", "build_contextual_grouping"),
        (".contextual_grouping", "build_contextual_grouping"),
    )

    for module_name, function_name in module_candidates:
        try:
            module = __import__(
                f"{__package__}{module_name}",
                fromlist=[function_name],
            )
        except ImportError:
            continue

        function = getattr(module, function_name, None)
        if callable(function):
            return cast(GroupingBuilder, function)

    raise RuntimeError(
        "Unable to import a contextual grouping builder. "
        "Pass build_contextual_grouping=... explicitly or complete grouping integration."
    )
