import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gate import check, init, parse_evidence  # noqa: E402

GOOD_BODY = """\
## Summary

Fix the widget.

### Evidence

- tests: command `pytest -q` — 34 passed
- merge-safety: git `abc1234` — rebased on main, no conflicts
"""


def _config(tmp_path, criteria=("tests", "merge-safety")):
    p = tmp_path / "evidence-gate.json"
    p.write_text(json.dumps({"criteria": {c: f"desc of {c}" for c in criteria}}))
    return p


def test_parse_extracts_typed_evidence():
    evidence, malformed = parse_evidence(GOOD_BODY)
    assert malformed == []
    assert evidence["tests"] == {"kind": "command", "ref": "pytest -q", "result": "34 passed"}
    assert evidence["merge-safety"]["kind"] == "git"


def test_double_hyphen_separator_accepted():
    body = "### Evidence\n- tests: command `make test` -- all green\n"
    evidence, malformed = parse_evidence(body)
    assert evidence["tests"]["result"] == "all green" and not malformed


def test_check_passes_when_all_criteria_covered(tmp_path, capsys):
    assert check(GOOD_BODY, _config(tmp_path)) == 0
    assert "COVERED    tests" in capsys.readouterr().out


def test_check_fails_on_missing_criterion(tmp_path, capsys):
    assert check(GOOD_BODY, _config(tmp_path, ("tests", "merge-safety", "deploy"))) == 1
    assert "MISSING    deploy" in capsys.readouterr().err


def test_check_fails_on_malformed_line(tmp_path, capsys):
    body = GOOD_BODY + "- deploy: I promise it works\n"
    assert check(body, _config(tmp_path)) == 1
    assert "MALFORMED" in capsys.readouterr().err


def test_unknown_kind_is_malformed(tmp_path, capsys):
    body = "### Evidence\n- tests: vibes `trust me` — fine\n"
    assert check(body, _config(tmp_path, ("tests",))) == 1


def test_missing_section_fails_with_init_hint(tmp_path, capsys):
    assert check("## Summary\nno evidence here\n", _config(tmp_path)) == 1
    assert "--init" in capsys.readouterr().err


def test_prose_claims_are_not_evidence(tmp_path, capsys):
    body = "### Evidence\n- tests: command `pytest` — passed\ntests pass I swear\n"
    assert check(body, _config(tmp_path, ("tests", "merge-safety"))) == 1


def test_init_round_trips_through_parser(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert init(tmp_path) == 0
    template = (tmp_path / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
    filled = template.replace("<command>", "pytest -q").replace("<observed result>", "9 passed")
    evidence, malformed = parse_evidence(filled)
    assert set(evidence) == {"tests", "verify"} and malformed == []


def test_cli_end_to_end(tmp_path):
    body = tmp_path / "body.md"
    body.write_text(GOOD_BODY)
    cfg = _config(tmp_path)
    r = subprocess.run([sys.executable, str(Path(__file__).parent.parent / "gate.py"),
                        "--body-file", str(body), "--config", str(cfg)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
