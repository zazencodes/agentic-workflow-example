# WORKFLOW: weekly-digest

Orchestrator spec for the `weekly-digest` workflow. Any CLI coding agent
(Claude Code, Codex, Antigravity, Hermes, …) should be able to run this cold,
with no context beyond this file.

**Stop and ask on any failure — never silently fall back, guess a value, or skip
the approval gate.**

One run covers **one ISO week**. It collects that week's merged commits and
closed issues, writes a human-readable digest, shows it to you once, and — only
after you approve — opens a pull request adding it to `CHANGELOG.md`.

## Shape: one gate, everything else automatic

There is exactly **one** approval gate: [Step 3](#step-3--gate-approve-the-digest),
after the draft is written and before the PR is opened. Everything before it is
automatic. Everything after it is automatic.

Nothing outside `state/digest-index.json` and the PR branch is ever written to.
The workflow never pushes to `main` and never merges its own PR.

## Constants

- Repo root: the directory containing this file.
- Scripts: `scripts/`. Run them with `python3` (stdlib only — no dependencies).
- State / idempotency index: `state/digest-index.json`, keyed by ISO week
  (`2026-W36`).
- Output template: `templates/digest.md`.
- Digest destination: `CHANGELOG.md` at the repo root, newest entry first.
- Branch naming: `digest/<iso-week>` (e.g. `digest/2026-W36`).
- Required tools: `git`, `gh` (GitHub CLI, authenticated), `python3`.

## Preflight

1. Verify the tools: `git --version`, `gh auth status`, `python3 --version`.
   If `gh` is unauthenticated, stop and ask — do not attempt a workflow-scoped
   fallback.
2. Confirm the working tree is clean (`git status --porcelain` is empty). If it
   is not, stop and ask; do not stash or commit unrelated changes.
3. Read `state/digest-index.json`. If the target week is already recorded with
   status `opened` or `merged`, stop and report the existing PR URL instead of
   producing a duplicate.

---

## Step 1 — Collect the week's activity (no gate)

```bash
python3 scripts/collect_activity.py --week last > /tmp/activity.json
```

- `--week last` (default) is the most recently completed ISO week. Use
  `--week 2026-W36` to target a specific one.
- The script shells out to `git log` and `gh issue list`, and prints a single
  JSON object: `{ week, range, commits[], issues[], stats }`.
- It is read-only. It never mutates the repository.
- If it exits non-zero, stop and show the error. Do not reconstruct the data by
  running `git log` yourself — a hand-rolled range is exactly the silent
  inconsistency this workflow exists to prevent.

If the week has no commits and no closed issues, stop and report "nothing to
digest for `<week>`". Do not open an empty PR.

---

## Step 2 — Write the digest (no gate)

This step is **yours**, not a script's. Read `/tmp/activity.json` and
`templates/digest.md`, then write the digest.

Rules for the prose:

- **Group by theme, not by commit.** Three commits fixing one bug are one line.
- **Write for a user of the project, not its author.** "Config files are now
  read from `~/.config`" beats "refactor: move config loader".
- **Lead with what changed for someone using it.** Internal refactors go last,
  or are omitted if they change nothing observable.
- **Match the voice of the existing `CHANGELOG.md`.** Read the previous two
  entries before writing. If the file does not exist yet, use the template's
  voice.
- **Never invent.** Every claim must trace to a commit or issue in the JSON. If
  something is ambiguous, say less rather than guessing.

Fill `templates/digest.md` and hold the result in memory. Do not write it to
`CHANGELOG.md` yet.

---

## Step 3 — GATE: approve the digest

Show the user:

1. The rendered digest, in full.
2. A one-line summary of what it was built from — commit count, issue count,
   date range.
3. The branch name and target file the PR will touch.

Then ask, exactly once:

> Open the PR with this digest? (yes / edit / no)

- **yes** — continue to Step 4.
- **edit** — apply the requested changes and re-present. Re-presenting is not a
  new gate; it is the same one, still open.
- **no** — stop. Record nothing in the index. Leave the tree clean.

**Do not run Step 4 without a yes.** This is the only irreversible step in the
workflow, and it is the only thing the user is asked about.

---

## Step 4 — Open the pull request (no gate)

```bash
python3 scripts/open_pr.py \
  --week 2026-W36 \
  --digest-file /tmp/digest.md
```

The script, in order:

1. Creates branch `digest/<week>` from the current `main`.
2. Prepends the digest to `CHANGELOG.md` (creating the file if absent).
3. Commits with `docs: weekly digest for <week>`.
4. Pushes and runs `gh pr create`, printing the PR URL.
5. Records `{ week, pr_url, status: "opened", commit_count, issue_count }` in
   `state/digest-index.json`.
6. Returns to the original branch, leaving the tree clean.

If any sub-step fails, the script leaves the index untouched and exits non-zero.
Report the failure verbatim and stop — do not retry with a different branch name.

---

## Approval gate (exactly one; never skip)

| Gate | When | Question |
|---|---|---|
| Step 3 | After the digest is written, before the PR is opened | Open the PR with this digest? |

There is no gate on collection, no gate on drafting, and no gate after the PR is
open. If you find yourself wanting to add one, the fix is usually to make the
step deterministic instead.

## Failure rules

- **Stop and ask.** Any non-zero exit, missing tool, or ambiguous state ends the
  run with a report. There is no "best effort" mode.
- **Never write outside the branch.** `main` is never committed to and never
  pushed to.
- **Never double-publish.** Check the index before Step 1 and write it only in
  Step 4, after the PR exists.
- **Resume, don't restart.** If the run is interrupted after Step 4's push but
  before the index write, re-running detects the existing remote branch and
  reconciles rather than opening a second PR.
