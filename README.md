# evidence-gate-action

[![evidence-gate (self)](https://github.com/cheshirecode/evidence-gate-action/actions/workflows/self-check.yml/badge.svg)](https://github.com/cheshirecode/evidence-gate-action/actions/workflows/self-check.yml)

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

## Releasing

`v1` is an annotated tag that moves with the v1 major line, so
`uses: cheshirecode/evidence-gate-action@v1` keeps working. Each release
also gets an immutable `vX.Y.Z` tag. To cut the next one:

```bash
git tag -a v1.1.0 -m "evidence-gate v1.1.0" <sha>
git tag -f -a v1   -m "evidence-gate v1 (major alias)" <sha>
git push origin v1.1.0
git push --force origin v1   # only the alias tag is ever moved
```

## Marketplace listing (blocked, needs a decision)

GitHub Marketplace asks for four things. This repo meets two of them
today:

| Requirement | State |
|---|---|
| Public repository | ✅ public |
| One `action.yml` at the repository root | ✅ one file, at the root |
| The `name:` in `action.yml` is unique | ❌ **taken** — see below |
| Publisher has 2FA on and accepts the Marketplace terms | 👤 user only |

**The name is taken, twice.** GitHub rejects an action name that matches
an existing Marketplace listing, and also one that matches any GitHub user
or organization the publisher does not own.

1. A Marketplace action already lists as *Evidence Gate*
   (`AlenKaleb/evidencegate-action`).
2. A GitHub organization `github.com/evidence-gate` exists. It was created
   on 2026-03-13 and it owns a repository also called
   `evidence-gate-action`.

So `name: evidence-gate` cannot be published as-is. The fix is to pick a
different `name:` in `action.yml` — the repository name and the `uses:`
path do not have to change, only the display name. This is a naming call,
so it is left open.

**Steps only the repository owner can do**, from the GitHub web UI:

1. Turn on two-factor authentication for the `cheshirecode` account.
2. Open the repository, then **Releases → Draft a new release**, pick the
   `v1.0.0` tag, and tick **Publish this Action to the GitHub Marketplace**.
3. Read and accept the GitHub Marketplace Developer Agreement. The checkbox
   appears in that same draft-release form.

None of this can be done from a script or a token; GitHub requires the
interactive form.
