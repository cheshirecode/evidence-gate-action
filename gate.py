#!/usr/bin/env python3
"""evidence-gate: map PR-body claims to typed evidence, deterministically.

Contract (all parsing is regex over a structured section — no LLM step, by
design): the PR body carries an `### Evidence` section with one line per
required criterion:

    ### Evidence
    - tests: command `pytest -q` — 34 passed
    - merge-safety: git `abc1234` — rebased on main, no conflicts

Required criteria come from `.github/evidence-gate.json`:

    {"criteria": {"tests": "the full suite passes", "merge-safety": "..."}}

Evidence kinds mirror the evidence-gate skill: command, artifact, git,
github, url. A criterion with no parseable evidence line fails the check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KINDS = ("command", "artifact", "git", "github", "url")

# `- <id>: <kind> `<ref>` — <result>`  (em-dash or double hyphen)
EVIDENCE_LINE = re.compile(
    r"^[-*]\s+(?P<id>[a-z][a-z0-9_-]*):\s+(?P<kind>[a-z]+)\s+`(?P<ref>[^`]+)`\s+(?:—|--)\s+(?P<result>\S.*)$"
)
SECTION = re.compile(r"^###\s+Evidence\s*$", re.M)

TEMPLATE = """\
## Summary

<!-- what and why -->

### Evidence

<!-- one line per required criterion: - <id>: <kind> `<ref>` — <result>
     kinds: command, artifact, git, github, url -->
{lines}
"""


def parse_evidence(body: str) -> tuple[dict[str, dict], list[str]]:
    """Return ({criterion: {kind, ref, result}}, [malformed lines])."""
    match = SECTION.search(body)
    if not match:
        return {}, []
    evidence: dict[str, dict] = {}
    malformed: list[str] = []
    for line in body[match.end():].splitlines():
        line = line.strip()
        if line.startswith("#"):
            break  # next section
        if not line.startswith(("-", "*")) or line.startswith(("<!--", "-->")):
            continue
        m = EVIDENCE_LINE.match(line)
        if not m:
            malformed.append(line)
            continue
        if m["kind"] not in KINDS:
            malformed.append(line)
            continue
        evidence[m["id"]] = {"kind": m["kind"], "ref": m["ref"], "result": m["result"]}
    return evidence, malformed


def check(body: str, config_path: Path) -> int:
    config = json.loads(config_path.read_text())
    criteria: dict[str, str] = config.get("criteria", {})
    if not criteria:
        print(f"evidence-gate: {config_path} declares no criteria", file=sys.stderr)
        return 2

    evidence, malformed = parse_evidence(body)
    rc = 0
    for line in malformed:
        print(f"MALFORMED  {line}", file=sys.stderr)
        rc = 1
    for cid, desc in criteria.items():
        if cid in evidence:
            e = evidence[cid]
            print(f"COVERED    {cid}: {e['kind']} `{e['ref']}` — {e['result']}")
        else:
            print(f"MISSING    {cid}: {desc} — add `- {cid}: <kind> `<ref>` — <result>` under ### Evidence", file=sys.stderr)
            rc = 1
    extra = set(evidence) - set(criteria)
    for cid in sorted(extra):
        print(f"EXTRA      {cid} (not required; kept for the record)")
    if not SECTION.search(body):
        print("MISSING    ### Evidence section entirely — run `gate.py --init` to seed the PR template", file=sys.stderr)
        rc = 1
    return rc


def init(root: Path) -> int:
    """Seed the structured contract: config + PR template. Resolves the
    chicken-and-egg adoption problem the council named — the tool ships the
    convention it checks."""
    config = root / ".github/evidence-gate.json"
    template = root / ".github/PULL_REQUEST_TEMPLATE.md"
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps(
            {"criteria": {"tests": "the test suite passes", "verify": "the change was verified working"}},
            indent=2) + "\n")
        print(f"wrote {config}")
    lines = "\n".join(
        f"- {cid}: command `<command>` — <observed result>"
        for cid in json.loads(config.read_text())["criteria"]
    )
    template.write_text(TEMPLATE.format(lines=lines))
    print(f"wrote {template}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="evidence-gate")
    ap.add_argument("--body-file", type=Path, help="file containing the PR body")
    ap.add_argument("--config", type=Path, default=Path(".github/evidence-gate.json"))
    ap.add_argument("--init", action="store_true", help="seed config + PR template in the current repo")
    ns = ap.parse_args(argv)
    if ns.init:
        return init(Path.cwd())
    if not ns.body_file:
        ap.error("--body-file is required unless --init")
    return check(ns.body_file.read_text(), ns.config)


if __name__ == "__main__":
    raise SystemExit(main())
