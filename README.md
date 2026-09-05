# evidence-gate-action

A GitHub Action that blocks pull requests whose claims carry no evidence.

Agent-written PRs are everywhere, and their descriptions routinely claim
things the diff does not prove — GitHub's own guidance is "no agent PR
without a review packet", and a 2026 study found 80% of agent test patches
carry weak or no oracles. This Action makes the review packet a merge gate.

**Deterministic by design.** No LLM, no network, no heuristics: the PR body
carries a structured `### Evidence` section, and a ~150-line regex parser
maps each required criterion to one typed evidence line. If it can't parse,
it fails — a claim that cannot be stated as `kind + ref + result` is not
evidence.

## The contract

```markdown
### Evidence

- tests: command `pytest -q` — 34 passed
- merge-safety: git `abc1234` — rebased on main, no conflicts
```

Kinds: `command`, `artifact`, `git`, `github`, `url`. Required criteria live
in `.github/evidence-gate.json`:

```json
{"criteria": {"tests": "the test suite passes", "merge-safety": "rebased and conflict-free"}}
```

## Setup (one command seeds the convention)

```bash
python3 gate.py --init   # writes evidence-gate.json + PULL_REQUEST_TEMPLATE.md
```

The generated PR template pre-fills one line per criterion, so authors (and
agents) fill in refs and results instead of inventing formats — the template
generator ships with the gate precisely so the convention exists before the
first PR.

```yaml
# .github/workflows/evidence-gate.yml
on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cheshirecode/evidence-gate-action@v1
```

## What it does not do

- Verify the evidence is *true* — it verifies the evidence is *stated*,
  typed, and complete. Reviewers replay refs; the gate guarantees there is
  something to replay.
- Parse free-text claims. Prose stays prose; only the structured section
  counts.

This repo dogfoods itself: every PR here passes through the action.
