# tests/test_filesystem_extractor.py

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import photoforge.metadata_extractors.filesystem as filesystem_module


def test_extract_filesystem_timestamp_candidates_with_birthtime(monkeypatch) -> None:
    fake_stat = SimpleNamespace(
        st_mtime=1704164645.0,
        st_ctime=1704168245.0,
        st_birthtime=1704171845.0,
    )

    monkeypatch.setattr(
        filesystem_module.os,
        "stat",
        lambda *args, **kwargs: fake_stat,
    )

    result = filesystem_module.extract_filesystem_timestamp_candidates(
        Path("dummy.jpg"),
        0.0,
    )

    assert tuple(candidate.source_detail for candidate in result) == (
        "filesystem_mtime",
        "filesystem_birthtime",
    )

    assert tuple(candidate.source_kind for candidate in result) == (
        "filesystem",
        "filesystem",
    )

    assert tuple(candidate.precision for candidate in result) == (
        "datetime",
        "datetime",
    )

    assert tuple(candidate.timezone_offset for candidate in result) == (
        None,
        None,
    )

    assert result[0].naive_timestamp == datetime.fromtimestamp(1704164645.0)
    assert result[1].naive_timestamp == datetime.fromtimestamp(1704171845.0)


def test_extract_filesystem_timestamp_candidates_without_birthtime(monkeypatch) -> None:
    fake_stat = SimpleNamespace(
        st_mtime=1704164645.0,
        st_ctime=1704168245.0,
    )

    monkeypatch.setattr(
        filesystem_module.os,
        "stat",
        lambda *args, **kwargs: fake_stat,
    )

    result = filesystem_module.extract_filesystem_timestamp_candidates(
        Path("dummy.jpg"),
        0.0,
    )

    assert tuple(candidate.source_detail for candidate in result) == (
        "filesystem_mtime",
    )


def test_invalid_timestamp_value_is_ignored(monkeypatch) -> None:
    fake_stat = SimpleNamespace(
        st_mtime=1704164645.0,
        st_ctime=float("nan"),
    )

    monkeypatch.setattr(
        filesystem_module.os,
        "stat",
        lambda *args, **kwargs: fake_stat,
    )

    result = filesystem_module.extract_filesystem_timestamp_candidates(
        Path("dummy.jpg"),
        0.0,
    )

    assert tuple(candidate.source_detail for candidate in result) == (
        "filesystem_mtime",
    )