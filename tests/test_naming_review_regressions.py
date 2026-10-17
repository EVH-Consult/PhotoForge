from dataclasses import replace
from pathlib import PureWindowsPath

import pytest

from photoforge import grouping
from photoforge.model import ContextualGrouping
from photoforge.naming import NamingRules
from photoforge.pipeline import run_pipeline
from photoforge.planner import plan_files
from photoforge.scanner import ScanResult
from tests.test_naming_rules import record


@pytest.mark.parametrize("name", ["CON .txt", "NUL .x", "COM1 .data", "LPT9  .out", "aux .x", "PRN   .jpg"])
@pytest.mark.parametrize("field", ["filename", "folder"])
def test_windows_device_names_with_predot_spaces_are_rejected(tmp_path, name, field):
    # PureWindowsPath is host-independent: Linux CI must reject Windows devices too.
    assert PureWindowsPath(name).is_reserved()
    rules = NamingRules(**{field: name})
    with pytest.raises(ValueError, match="unsafe or overlong"):
        plan_files([record(tmp_path / "input.jpg")], output_path=tmp_path / "out", naming_rules=rules)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("name", ["CONx .txt", "xCON .txt", "COM10 .data"])
def test_nondevice_lookalikes_remain_usable(tmp_path, name):
    assert not PureWindowsPath(name).is_reserved()
    plan = plan_files([record(tmp_path / "input.jpg")], naming_rules=NamingRules(filename=name))
    assert plan.actions[0].target_path.name == name + ".jpg"


@pytest.mark.parametrize("extension,basename_length,accepted", [
    (".jpg", 116, True), (".jpg", 117, False), (".jpg", 120, False),
    (".heic", 115, True), (".heic", 116, False),
])
def test_final_filename_limit_includes_extension(tmp_path, extension, basename_length, accepted):
    item = replace(record(tmp_path / ("input" + extension)), canonical_extension=extension)
    rules = NamingRules(filename="x" * basename_length)
    if accepted:
        plan = plan_files([item], naming_rules=rules)
        assert len(plan.actions[0].target_path.name) == 120
    else:
        with pytest.raises(ValueError, match="overlong"):
            plan_files([item], naming_rules=rules)


@pytest.mark.parametrize("length,accepted", [(115, True), (116, False)])
def test_pair_checks_both_final_extensions_before_returning_actions(tmp_path, length, accepted):
    still = replace(record(tmp_path / "pair.heic"), canonical_extension=".heic",
                    live_photo_pair_id="pair", live_photo_role="still")
    motion = replace(record(tmp_path / "pair.mov", "b" * 64), canonical_extension=".mov",
                     live_photo_pair_id="pair", live_photo_role="motion")
    rules = NamingRules(filename="x" * length)
    if accepted:
        plan = plan_files([motion, still], naming_rules=rules)
        assert sorted(len(a.target_path.name) for a in plan.actions) == [119, 120]
        assert len({a.target_path.stem for a in plan.actions}) == 1
    else:
        with pytest.raises(ValueError, match="overlong"):
            plan_files([motion, still], naming_rules=rules)


@pytest.mark.parametrize("length,accepted", [(120, True), (121, False)])
def test_final_folder_component_limit(tmp_path, length, accepted):
    rules = NamingRules(folder="x" * length)
    if accepted:
        plan = plan_files([record(tmp_path / "input.jpg")], output_path=tmp_path / "out", naming_rules=rules)
        assert len(plan.actions[0].target_path.parent.name) == 120
    else:
        with pytest.raises(ValueError, match="overlong"):
            plan_files([record(tmp_path / "input.jpg")], output_path=tmp_path / "out", naming_rules=rules)


@pytest.mark.parametrize("event_naming", [False, True])
def test_pipeline_computes_grouping_once_for_reporting_and_naming(tmp_path, monkeypatch, event_naming):
    records = (record(tmp_path / "a.jpg"), record(tmp_path / "b.jpg", "b" * 64))
    scan = ScanResult(records, (), (), 2, 2)
    original = grouping.build_contextual_grouping
    calls = []
    def counted(values):
        calls.append(values)
        return original(values)
    monkeypatch.setattr(grouping, "build_contextual_grouping", counted)
    monkeypatch.setattr("photoforge.pipeline.scan_directory", lambda _: pytest.fail("unexpected rescan"))
    rules = NamingRules(folder="{event}", use_context_groups=True) if event_naming else NamingRules()
    plan, contextual = run_pipeline(tmp_path, scan_result=scan, output_path=tmp_path / "out", naming_rules=rules)
    assert calls == [records]
    if event_naming:
        assert {a.target_path.parent.name for a in plan.actions} == {contextual.groups[0].group_id}
    else:
        assert {a.target_path.parent.name for a in plan.actions} == {"03"}


def test_direct_planner_computes_one_grouping_when_not_supplied(tmp_path, monkeypatch):
    original = grouping.build_contextual_grouping
    calls = []
    def counted(values):
        calls.append(values)
        return original(values)
    monkeypatch.setattr(grouping, "build_contextual_grouping", counted)
    records = (record(tmp_path / "a.jpg"),)
    plan_files(records, output_path=tmp_path / "out", naming_rules=NamingRules(folder="{event}", use_context_groups=True))
    assert calls == [records]


def test_empty_event_snapshot_computes_once_without_synthetic_groups(tmp_path, monkeypatch):
    original = grouping.build_contextual_grouping
    calls = []
    def counted(values):
        calls.append(values)
        return original(values)
    monkeypatch.setattr(grouping, "build_contextual_grouping", counted)
    plan, contextual = run_pipeline(tmp_path, scan_result=ScanResult((), (), (), 0, 0),
                                    output_path=tmp_path / "out",
                                    naming_rules=NamingRules(folder="{event}", use_context_groups=True))
    assert calls == [()]
    assert plan.actions == () and contextual.groups == ()


def test_supplied_event_grouping_must_cover_the_same_snapshot(tmp_path):
    with pytest.raises(ValueError, match="same complete record snapshot"):
        plan_files([record(tmp_path / "a.jpg")], output_path=tmp_path / "out",
                   naming_rules=NamingRules(folder="{event}", use_context_groups=True),
                   contextual_grouping=ContextualGrouping(()))


def test_pipeline_preserves_default_injected_planner_arguments(tmp_path):
    from photoforge.model import PlanResult
    calls = []
    def planner(records, *args, **kwargs):
        calls.append((records, args, kwargs))
        return PlanResult((), (), ())
    run_pipeline(tmp_path, "sentinel", scan_result=ScanResult((), (), (), 0, 0), plan_files=planner, custom="value")
    assert calls == [((), ("sentinel",), {"custom": "value"})]
