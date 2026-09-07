# AGENTS.md

## Project Instructions

- Treat this file as the canonical agent context for the repo. `CLAUDE.md` is a
  symlink to it.
- This repo is a **teaching example**, published alongside *A Developer's Guide to
  Agentic Workflows*. Clarity beats cleverness in every tradeoff. Someone should
  be able to read the whole thing in ten minutes.
- `WORKFLOW.md` is the artifact the guide points at. Keep it self-contained: an
  agent with no prior context must be able to run it cold. Do not move
  information out of it into this file.
- Scripts are **stdlib-only Python 3**. No dependencies, no package manager, no
  virtualenv. If a change needs a third-party library, the change is wrong for
  this repo.
- Keep the four parts visible and named: the spec, the deterministic scripts, the
  state index, the single approval gate. The structure *is* the lesson.
- Scripts fail loud. No silent fallbacks, no best-effort modes, no retry loops
  that hide an error. `collect_activity.py` skipping issues when `gh` is missing
  is the one documented exception, and it warns on stderr.

## Repo Shape

- `WORKFLOW.md` — the orchestrator spec. Read it before touching anything else.
- `scripts/collect_activity.py` — read-only; one ISO week of git + gh activity
  as JSON.
- `scripts/open_pr.py` — the only irreversible step; branch, commit, PR, index
  write. Runs after the approval gate.
- `state/digest-index.json` — idempotency index keyed by ISO week. Committed
  empty; real runs populate it.
- `templates/digest.md` — the shape the agent fills in at Step 2.
- `docs/assets/` — README banner.

## Conventions

- Short, single-line commit messages. Never add AI attribution or co-author
  trailers.
- Keep `README.md` and `WORKFLOW.md` in sync when the file tree changes — both
  show it.
