# AGENTS.md

## Purpose of this project

- This repo is a **teaching example**, published alongside *A Developer's Guide to
  Agentic Workflows* on zazencodes.com (a PDF that newsletter members receive).

## Running the workflow

**When the user asks for a repo digest, a changelog, or a summary of what has
shipped — run `WORKFLOW.md`.**

The workflow always operates on **another repository on the user's machine**,
given as a path. This repo is the tool, never the subject.

Phrases that mean "run the workflow":

- "run the repo changelog workflow" / "run the repo digest" / "run the digest
  workflow" / "run WORKFLOW.md"
- "write up what's changed in ~/code/my-project since the last release"
- "what shipped recently in <project>? open a PR for it"
- "catch me up on what happened while I was out"
- any of the above with a path attached: "run the repo changelog workflow for
  ~/code/my-project"
- any request naming a starting point: "digest since v1.4.0", "digest since August"

What to do when one of those arrives:

1. **Read `WORKFLOW.md` end to end before doing anything.** It is the program.
   This file is not a summary of it — do not act on your memory of the steps.
2. Follow it in order, starting at Preflight. Do not skip steps, reorder them,
   or improvise a shortcut because the repo looks small.
3. Stop at the Step 3 gate and wait for a real answer. Never assume approval.
4. **If the request did not include a repository path, ask for one first.** That
   is Preflight step 1, and it is the one thing you cannot infer. Do not assume
   the current directory, do not go looking for likely projects, and never point
   it at this repo — the scripts refuse that outright.
5. If the user named a starting point ("since v1.4.0", "since August"), pass it
   through as `--since`. If not, Preflight says how to pick one.

What *not* to do:

- Do not hand-roll the digest by running `git log` yourself and writing a
  summary in chat. The scripts and the state file exist so the run is repeatable
  and so a re-run cannot double-publish. A one-off answer in the transcript
  defeats both.
- Do not offer to schedule it, add a cron job, or wire up a GitHub Action. It is
  meant to be run by hand, when someone wants a digest.
- Do not run it against this repo to "demonstrate" it. There is nothing to
  digest here, and the scripts exit non-zero if you try.
- Do not treat a question *about* the workflow ("what does step 2 do?") as a
  request to run it.

## Project Instructions

- `WORKFLOW.md` is the artifact the guide points at. Keep it self-contained: an
  agent with no prior context must be able to run it cold. Do not move
  information out of it into this file — this file says *when* to run the
  workflow, `WORKFLOW.md` says *how*.
- Scripts are **stdlib-only Python 3**. No dependencies, no package manager, no
  virtualenv. If a change needs a third-party library, the change is wrong for
  this repo.
- Keep the four parts visible and named: the spec, the deterministic scripts, the
  state file, the single approval gate. The structure *is* the lesson.
- Both scripts take `--repo` and do all their git work there. Nothing may quietly
  default to the current directory — that is how a teaching example ends up
  committing to the wrong project.
- Scripts fail loud. No silent fallbacks, no best-effort modes, no retry loops
  that hide an error. `collect_activity.py` skipping issues when `gh` is missing
  is the one documented exception, and it warns on stderr.

## Repo Shape

- `WORKFLOW.md` — the orchestrator spec. Read it before touching anything else.
- `scripts/collect_activity.py` — read-only; git + gh activity in `--repo` since
  a given date, tag, or commit, as JSON.
- `scripts/open_pr.py` — the only irreversible step; branch, commit and PR in
  `--repo`, plus the state write here. Runs after the approval gate.
- `state/workflow-state.json` — the run in progress (`active_run`) plus, per
  target repo path, the idempotency index (`repos[<path>].runs`) keyed by the
  commit each digest covered up to. One file serves every project. Committed
  empty; real runs populate it. Run artifacts land beside it and are gitignored.
- `templates/digest.md` — the shape the agent fills in at Step 2.
- `AGENTS.md` — this file: the natural-language trigger that maps a user's
  request onto `WORKFLOW.md`. Agents read it automatically at session start.
  `CLAUDE.md` is a symlink to it.
- `docs/assets/` — README banner.

## Conventions

- Keep `README.md` and `WORKFLOW.md` in sync when the file tree changes.
