# WORKFLOW: repo-digest

Orchestrator spec for the `repo-digest` workflow. Any CLI coding agent
(Claude Code, Codex, Antigravity, Hermes, …) should be able to run this cold,
with no context beyond this file.

**Stop and ask on any failure — never silently fall back, guess a value, or skip
the approval gate.**

It runs **on demand**, whenever someone asks — there is no schedule and nothing
to install.

**It digests a different repository.** This repo holds the spec, the scripts and
the state; the repo being digested is a project somewhere else on the user's
machine. Nothing here is ever the target. The branch, the `CHANGELOG.md` entry,
the commit and the PR all happen over there.

One run covers everything that has landed in the target since a starting point
you choose: a date, a tag, a release, or the last digest. It collects the commits
and closed issues in that range, writes a human-readable digest, shows it to you
once, and — only after you approve — opens a pull request adding it to the
target's `CHANGELOG.md`.

## Shape: one gate, everything else automatic

There is exactly **one** approval gate: [Step 3](#step-3--gate-approve-the-digest),
after the draft is written and before the PR is opened. Everything before it is
automatic. Everything after it is automatic.

In this repo, nothing outside `state/` is ever written. In the target repo,
nothing outside the digest branch is ever written — the workflow never commits to
the default branch, never pushes to it, and never merges its own PR.

## Constants

- Workflow repo: the directory containing this file. Holds the scripts and the
  state. Never the thing being digested.
- Target repo: the project being digested, given by the user as a path. Every
  script takes it as `--repo`.
- Scripts: `scripts/`. Run them with `python3` (stdlib only — no dependencies).
- State / checkpoint file: `state/workflow-state.json`, in **this** repo. Tracks
  the run in progress (`active_run`) and, per target repo path, every digest
  already published (`repos[<path>].runs`, keyed by the commit it covered up to).
  One state file serves every project you point the workflow at.
- Run artifacts: `state/activity.json` and `state/digest.md`. Both are
  gitignored. They live beside the state file so an interrupted run can be
  resumed from disk rather than restarted.
- Output template: `templates/digest.md`.
- Digest destination: `CHANGELOG.md` at the **target** repo root, newest entry
  first. Created if it does not exist.
- Base branch: the target's own default branch, detected from `origin/HEAD`.
- Branch naming: `digest/<short-sha>`, where the sha is the commit the digest
  covers up to (e.g. `digest/a1b2c3d`). `open_pr.py` derives it; you never pick it.
- Required tools: `git`, `gh` (GitHub CLI, authenticated), `python3`.

## Preflight

1. **Ask which repository to digest.** If the user already gave a path ("run the
   digest for ~/code/my-project"), use it and say which path you resolved. If
   they did not, ask before doing anything else:

   > Which repository should I digest? Give me the path on your machine.

   This is a **question, not a gate** — it is cheap, it comes before any work,
   and it is the only thing you need from the user until Step 3. Never guess a
   path, never scan the disk for candidates, and never fall back to this repo.
2. Resolve and validate the target. It must be a directory, a git repository,
   and not this workflow repo. Both scripts check all three and refuse loudly,
   but check yourself before you start so you fail in one second rather than
   three steps in.
3. Verify the tools: `git --version`, `gh auth status`, `python3 --version`.
   If `gh` is unauthenticated, stop and ask — do not attempt a workflow-scoped
   fallback. Confirm the target has a remote (`git -C <repo> remote get-url origin`);
   without one there is nowhere to open a PR.
4. Confirm the **target's** working tree is clean
   (`git -C <repo> status --porcelain` is empty). If it is not, stop and ask; do
   not stash or commit someone else's work in progress.
5. Settle the starting point, in this order of preference:
   - what the user named ("since v1.4.0", "since August", "since my last digest");
   - the newest key in `repos[<target>].runs`, if there is one — that is where
     the previous digest for this project stopped;
   - otherwise the default: the last 7 days.

   Say which one you picked before you start collecting.
6. Read `state/workflow-state.json`:
   - If `repos[<target>].runs` already contains an entry whose key is the
     target's current `HEAD`, nothing has landed since the last digest. Stop and
     report that PR URL.
   - If `active_run` exists **for this same target**, resume it: skip every step
     at or below `last_completed_step`, reusing the artifacts already on disk. If
     it exists for a *different* target, say so and ask before overwriting it.
   - Otherwise set `active_run` to
     `{ "repo": "<target>", "since": "<starting point>", "last_completed_step": 0, "started_at": "<iso-timestamp>" }`,
     leaving `repos` untouched.

---

## Step 1 — Collect activity (no gate)

Start the collection script as a background process and, while it runs, read the
context you will need in Step 2. The two are independent, so do them at once:

- **Background:**
  ```bash
  python3 scripts/collect_activity.py --repo <target> --since <starting-point> > state/activity.json
  ```
  `--since` takes a `YYYY-MM-DD` date or any commit, tag, or branch; omit it for
  the last 7 days. It prints `{ repo, since, head, commits[], issues[], stats }` —
  `git log` plus `gh issue list` in the target, no judgment. It is read-only:
  nothing in the target is touched until Step 4.
- **Meanwhile:** read the last two entries of the **target's** `CHANGELOG.md` so
  you know the voice to match. If it does not have one yet, read
  `templates/digest.md` instead, and look at its README for the project's voice.

Wait for the script to finish. If it exits non-zero, stop and show the error.

If the range has no commits and no closed issues, stop and report that there is
nothing to digest. Do not open an empty PR.

**Checkpoint:** set `active_run.last_completed_step` to `1`.

---

## Step 2 — Write the digest (no gate)

This step is **yours**, not a script's. Synthesize `state/activity.json` and
`templates/digest.md` into the digest.

Rules for the prose:

- **Group by theme, not by commit.** Three commits fixing one bug are one line.
- **Write for a user of the project, not its author.** "Config files are now
  read from `~/.config`" beats "refactor: move config loader".
- **Lead with what changed for someone using it.** Internal refactors go last,
  or are omitted if they change nothing observable.
- **Match the voice you read in Step 1.**
- **Never invent.** Every claim must trace to a commit or issue in the JSON. If
  something is ambiguous, say less rather than guessing.

Save the rendered markdown to `state/digest.md`.

**Checkpoint:** set `active_run.last_completed_step` to `2`.

---

## Step 3 — GATE: approve the digest

Show the user:

1. The rendered digest, in full.
2. A one-line summary of what it was built from — commit count, issue count,
   date range.
3. The target repo path, the branch name, and the file the PR will touch.

Then ask, exactly once:

> Open the PR with this digest? (yes / edit / no)

- **yes** — continue to Step 4.
- **edit** — apply the requested changes, update `state/digest.md`, and re-present.
  Re-presenting is not a new gate; it is the same one, still open.
- **no** — stop. Clear `active_run` in `state/workflow-state.json`. Leave the tree clean.

**Do not run Step 4 without a yes.** This is the only irreversible step in the
workflow, and it is the only thing the user is asked about.

---

## Step 4 — Open the pull request (no gate)

```bash
python3 scripts/open_pr.py --repo <target> --digest-file state/digest.md
```

The script, in order:

1. Detects the target's default branch and reads its short sha — the commit this
   digest covers up to.
2. Creates branch `digest/<short-sha>` in the target, from that default branch.
3. Prepends the digest to the target's `CHANGELOG.md` (creating it if absent).
4. Commits with `docs: repo digest through <short-sha>`.
5. Pushes and runs `gh pr create` in the target, printing the PR URL.
6. Records `{ pr_url, status: "opened", branch, base, opened_at }` under
   `repos[<target>].runs[<short-sha>]` in **this** repo's state file, and clears
   `active_run`.
7. Returns the target to the branch it was on, leaving its tree clean.

If any sub-step fails, the script leaves the state file untouched and exits
non-zero.
Report the failure verbatim and stop — do not retry with a different branch name.

---

## Approval gate (exactly one; never skip)

| Gate | When | Question |
|---|---|---|
| Step 3 | After the digest is written, before the PR is opened | Open the PR with this digest? |

Asking for the target repo path in Preflight is **not** a gate. It is a cheap
question asked before any work starts, and the run does not stall on it in the
middle of something. Gates are for stopping the machine; questions are for
starting it.

There is no gate on collection, no gate on drafting, and no gate after the PR is
open. If you find yourself wanting to add one, the fix is usually to make the
step deterministic instead.

## Failure rules

- **Stop and ask.** Any non-zero exit, missing tool, or ambiguous state ends the
  run with a report. There is no "best effort" mode.
- **Never write outside the branch.** The target's default branch is never
  committed to and never pushed to. Nothing outside the target's `CHANGELOG.md`
  is edited.
- **Never double-publish.** Check `repos[<target>].runs` in preflight and write
  to it only in Step 4, after the PR exists. The key is the commit the digest
  covered, so a second run against an unchanged target is refused by the script
  as well.
- **Resume, don't restart.** If a run is interrupted, `active_run` says which
  step finished last and the artifacts beside it are still on disk. Pick up from
  there instead of starting over.
