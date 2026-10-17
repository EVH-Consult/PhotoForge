"""Explicit portable naming templates; no arbitrary expressions or lookups."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from string import Formatter
import unicodedata

DEFAULT_FILENAME = "{year}-{month}-{day}_{hour}{minute}{second}_{short_hash}"
DEFAULT_FOLDER = "{year}/{month}/{day}"
FIELDS = {"year", "month", "day", "hour", "minute", "second", "hash",
          "short_hash", "camera_make", "camera_model", "event"}
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))}


def validate_template(template: str, *, folder: bool, groups: bool) -> None:
    if not isinstance(template, str) or not template or len(template) > 1024:
        raise ValueError("naming template must be a nonempty string of at most 1024 characters")
    if "\\" in template or (not folder and "/" in template):
        raise ValueError("only folder templates may contain '/' separators")
    for part in template.split("/"):
        if not part or part in {".", ".."}:
            raise ValueError("naming template contains an empty or traversal component")
        for literal, field, spec, conversion in Formatter().parse(part):
            if re.search(r'[^A-Za-z0-9._ -]', literal):
                raise ValueError("naming literals must be portable ASCII characters")
            if field is not None and (field not in FIELDS or spec or conversion):
                raise ValueError("unknown naming field or unsupported format/conversion")
            if field == "event" and not groups:
                raise ValueError("{event} requires use_context_groups=true")


@dataclass(frozen=True)
class NamingRules:
    filename: str = DEFAULT_FILENAME
    folder: str = DEFAULT_FOLDER
    use_context_groups: bool = False

    def __post_init__(self):
        if type(self.use_context_groups) is not bool:
            raise ValueError("use_context_groups must be boolean")
        validate_template(self.filename, folder=False, groups=self.use_context_groups)
        validate_template(self.folder, folder=True, groups=self.use_context_groups)


def load_naming_rules(path: Path) -> NamingRules:
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = {"version", "filename", "folder", "use_context_groups"}
    if not isinstance(data, dict) or set(data) - allowed or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("naming configuration requires version 1 and known keys only")
    return NamingRules(**{key: value for key, value in data.items() if key != "version"})


def portable_metadata(value: str | None) -> str:
    if not value:
        return "unknown"
    result = re.sub(r"[^A-Za-z0-9._-]+", "_", unicodedata.normalize("NFKC", value)).strip("._")
    result = result[:80] or "unknown"
    if result.split(".")[0].upper() in RESERVED:
        result = "_" + result
    return result


def validate_component(component: str) -> None:
    """Validate a complete portable path component, including its extension."""
    # Windows ignores spaces before the first dot when recognizing devices.
    device_stem = component.split(".", 1)[0].rstrip(" ").upper()
    if (not component or component in {".", ".."} or component[-1] in ". "
            or len(component) > 120 or device_stem in RESERVED):
        raise ValueError("naming template produces an unsafe or overlong component")


def render_template(template: str, record, asset_hash: str, event: str | None) -> str:
    stamp = record.timestamp
    values = {"year": f"{stamp.year:04d}", "month": f"{stamp.month:02d}",
              "day": f"{stamp.day:02d}", "hour": f"{stamp.hour:02d}",
              "minute": f"{stamp.minute:02d}", "second": f"{stamp.second:02d}",
              "hash": asset_hash, "short_hash": asset_hash[:8], "event": event or "unknown",
              "camera_make": portable_metadata(record.metadata.camera_make if record.metadata else None),
              "camera_model": portable_metadata(record.metadata.camera_model if record.metadata else None)}
    rendered = template.format_map(values)
    for component in rendered.split("/"):
        validate_component(component)
    return rendered
