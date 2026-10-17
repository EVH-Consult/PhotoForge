import io
import json
from pathlib import Path

import pytest
from PIL import Image

from photoforge import cli


def media(tmp_path):
    for name in ("a", "b"):
        Image.new("RGB", (1, 1)).save(tmp_path / f"IMG_20240102_030405_{name}.jpg")
    return [str(tmp_path)]


def test_json_unchanged_with_verbosity_and_phase_progress(tmp_path, capsys):
    args = media(tmp_path)
    assert cli.main(args + ["--json"]) == 0
    original = capsys.readouterr()
    assert cli.main(args + ["--json", "--verbosity", "verbose", "--progress"]) == 0
    changed = capsys.readouterr()
    assert changed.out == original.out
    assert "scanning" in changed.err and "planning" in changed.err and "report complete" in changed.err
    assert "duplicate-group" in changed.err
    assert "canonical:" in changed.err and "duplicate:" in changed.err
    json.loads(changed.out)


def test_quiet_json_is_complete_and_console_is_compact(tmp_path, capsys):
    args = media(tmp_path)
    cli.main(args + ["--json", "--verbosity", "quiet"])
    assert len(json.loads(capsys.readouterr().out)["records"]) == 2
    cli.main(args + ["--verbosity", "quiet"])
    output = capsys.readouterr().out
    assert len(output.splitlines()) == 1
    assert "duplicates: 1" in output


def test_diff_is_stable_limited_and_read_only(tmp_path, monkeypatch, capsys):
    args = media(tmp_path)
    Image.new("RGB", (1, 1), (255, 0, 0)).save(tmp_path / "IMG_20240102_030405_c.jpg")
    monkeypatch.setattr(cli, "apply_actions", lambda _: pytest.fail("diff mutated input"))
    for _ in range(2):
        assert cli.main(args + ["--diff", "--limit", "1"]) == 0
        output = capsys.readouterr().out
        if _ == 0:
            first = output
        assert output == first
    assert "DRY-RUN PLAN" in first and "- " in first and "+ " in first
    assert "1 more actions omitted" in first
    assert len(list(tmp_path.iterdir())) == 3


class Interactive(io.StringIO):
    def isatty(self):
        return True


@pytest.mark.parametrize("answer,expected", [("y\n", 0), (" YES \n", 0), ("n\n", 1), ("\n", 1), ("", 1)])
def test_opt_in_confirmation_reports_before_mocked_mutation(tmp_path, monkeypatch, capsys, answer, expected):
    args = media(tmp_path)
    monkeypatch.setattr(cli.sys, "stdin", Interactive(answer))
    applied = []
    def apply(actions):
        output = capsys.readouterr()
        assert output.out and "Apply this plan?" in output.err
        applied.extend(actions)
    monkeypatch.setattr(cli, "apply_actions", apply)
    assert cli.main(args + ["--apply", "--confirm"]) == expected
    assert bool(applied) == (expected == 0)


def test_noninteractive_confirmation_fails_closed(tmp_path, monkeypatch, capsys):
    args = media(tmp_path)
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO("yes\n"))
    monkeypatch.setattr(cli, "apply_actions", lambda _: pytest.fail("unexpected mutation"))
    assert cli.entrypoint(args + ["--apply", "--confirm", "--json"]) == 2
    output = capsys.readouterr()
    json.loads(output.out)
    assert json.loads(output.err)["error"]["code"] == "invalid_input"


@pytest.mark.parametrize("flags", [["--confirm"], ["--diff", "--apply"], ["--diff", "--json"],
                                    ["--limit", "1"], ["--diff", "--limit", "0"]])
def test_invalid_flag_combinations_fail_before_scan(tmp_path, monkeypatch, capsys, flags):
    monkeypatch.setattr(cli, "scan_directory", lambda *a, **k: pytest.fail("unexpected scan"))
    with pytest.raises(SystemExit) as exc:
        cli.main([str(tmp_path), *flags])
    assert exc.value.code == 2
    assert capsys.readouterr().out == ""


def test_missing_input_has_deterministic_json_error_without_traceback(tmp_path, capsys):
    args = [str(tmp_path / "missing"), "--json"]
    outputs = []
    for _ in range(2):
        assert cli.entrypoint(args) == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        outputs.append(captured.err)
    assert outputs[0] == outputs[1]
    assert json.loads(outputs[0])["error"]["code"] == "invalid_input"
    assert "Traceback" not in outputs[0]


def test_default_dry_run_never_prompts_or_applies(tmp_path, monkeypatch, capsys):
    args = media(tmp_path)
    class Forbidden(io.StringIO):
        def readline(self, *a):
            pytest.fail("default path prompted")
    monkeypatch.setattr(cli.sys, "stdin", Forbidden())
    monkeypatch.setattr(cli, "apply_actions", lambda _: pytest.fail("default path applied"))
    assert cli.entrypoint(args) == 0


def test_explicit_apply_keeps_noninteractive_interface_and_reports_first(tmp_path, monkeypatch, capsys):
    args = media(tmp_path)
    def apply(actions):
        assert capsys.readouterr().out
        assert tuple(actions)
    monkeypatch.setattr(cli, "apply_actions", apply)
    assert cli.entrypoint(args + ["--apply"]) == 0


def test_filesystem_failure_is_reported_without_platform_exception_text(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "scan_directory", lambda *a, **k: (_ for _ in ()).throw(OSError("platform-dependent message")))
    assert cli.entrypoint([str(tmp_path), "--json"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err) == {"error": {"code": "filesystem_error", "message": "filesystem operation failed"}}
