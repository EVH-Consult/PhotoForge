"""Deterministic presentation helpers; never mutate plans or media."""
from collections import Counter, defaultdict
import json


def render_summary(plan):
    actions = Counter(action.action for action in plan.actions)
    duplicates = sum(not record.canonical for record in plan.records)
    return (f"Records: {len(plan.records)}; duplicates: {duplicates}; "
            f"corrupt: {len(plan.corrupt_files)}; "
            + "; ".join(f"{key}: {actions[key]}" for key in sorted(actions)))


def render_diff(plan, *, limit=None):
    actions = sorted(plan.actions, key=lambda action: (str(action.source_path), str(action.target_path)))
    lines = ["DRY-RUN PLAN" , render_summary(plan)]
    visible = actions if limit is None else actions[:limit]
    for action in visible:
        source = json.dumps(str(action.source_path), ensure_ascii=False)
        target = json.dumps(str(action.target_path), ensure_ascii=False)
        if action.action in {"rename", "move"}:
            lines.extend((f"- {source}", f"+ {target} [{action.action}]"))
        else:
            lines.append(f"! {action.action}: {source} -> {target}")
    if len(visible) < len(actions):
        lines.append(f"... {len(actions) - len(visible)} more actions omitted")
    return "\n".join(lines)


def render_duplicate_details(plan):
    groups = defaultdict(list)
    for record in plan.records:
        if record.duplicate_group_size > 1:
            groups[record.duplicate_group_id].append(record)
    lines = []
    for group_id in sorted(groups):
        members = sorted(groups[group_id], key=lambda item: str(item.path))
        lines.append(f"duplicate-group {group_id}:")
        for member in members:
            role = "canonical" if member.canonical else "duplicate"
            lines.append(f"  {role}: {json.dumps(str(member.path), ensure_ascii=False)}")
    return "\n".join(lines)
