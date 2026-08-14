from __future__ import annotations

from pathlib import Path
import shutil
from typing import Iterable

from .model import PlannedAction


def apply_actions(actions: Iterable[PlannedAction]) -> None:
    for action in actions:
        _apply_action(action)


def _apply_action(action: PlannedAction) -> None:
    if action.action == "skip":
        return

    if action.action == "collision":
        return

    if action.action == "rename" or action.action == "move":
        _ensure_parent_directory(action.target_path)
        _move_without_overwrite(action.source_path, action.target_path)
        return

    raise ValueError(f"Unsupported action: {action.action}")


def _ensure_parent_directory(target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)


def _move_without_overwrite(source_path: Path, target_path: Path) -> None:
    if target_path.exists():
        return

    shutil.move(str(source_path), str(target_path))
