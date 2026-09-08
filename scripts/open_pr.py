#!/usr/bin/env python3
"""Open the repo-digest pull request in a target repository.

Deterministic other half of the `repo-digest` workflow: take an approved digest
and turn it into a branch, a commit, and a PR — the same way every time.

    python3 scripts/open_pr.py --repo ~/code/my-project --digest-file state/digest.md

`--repo` is the project being digested, somewhere else on your machine. The
branch, the `CHANGELOG.md` edit, the commit and the PR all happen there. Only
the state file is written here, in the workflow repo.

Each digest is recorded against the commit it covers, so re-running against an
unchanged repo is refused rather than opening a second, identical PR.

This is the only irreversible step in the workflow. It runs only after the
Step 3 approval gate. Stdlib only; requires `git` and an authenticated `gh`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = TOOL_ROOT / "state" / "workflow-state.json"


def run(cmd: list[str], cwd: Path) -> str:
    """Run a command in `cwd`, returning stdout. Raises on failure."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"{' '.join(cmd)} failed ({proc.returncode}): {stderr}")
    return proc.stdout


def resolve_repo(raw: str) -> Path:
    """Validate the target repository path. Never defaults to the workflow repo."""
    repo = Path(raw).expanduser().resolve()
    if not repo.is_dir():
        raise SystemExit(f"--repo {raw!r} is not a directory")
    if repo == TOOL_ROOT:
        raise SystemExit(
            "--repo points at the workflow repo itself. Point it at the project "
            "you want a changelog for."
        )
    try:
        run(["git", "rev-parse", "--git-dir"], cwd=repo)
    except RuntimeError as exc:
        raise SystemExit(f"--repo {raw!r} is not a git repository.\n{exc}") from exc
    return repo


def default_base(repo: Path) -> str:
    """The target's default branch, from `origin/HEAD`; falls back to `main`."""
    try:
        ref = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo).strip()
        return ref.rsplit("/", 1)[-1]
    except RuntimeError:
        return "main"


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"active_run": None, "repos": {}}
    return json.loads(STATE_PATH.read_text())


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def require_clean_tree(repo: Path) -> None:
    if run(["git", "status", "--porcelain"], cwd=repo).strip():
        raise RuntimeError(f"{repo} has uncommitted changes; commit or stash first")


def prepend_changelog(changelog: Path, digest: str) -> None:
    existing = changelog.read_text() if changelog.exists() else "# Changelog\n"
    header, _, body = existing.partition("\n")
    changelog.write_text(f"{header}\n\n{digest.strip()}\n{body}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="path to the repository being digested")
    parser.add_argument("--digest-file", required=True, type=Path)
    parser.add_argument("--base", help="base branch (default: the target's default branch)")
    parser.add_argument("--dry-run", action="store_true", help="show the plan, change nothing")
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    base = args.base or default_base(repo)
    changelog = repo / "CHANGELOG.md"
    head = run(["git", "rev-parse", "--short", base], cwd=repo).strip()

    state = load_state()
    runs = state.setdefault("repos", {}).setdefault(str(repo), {}).setdefault("runs", {})
    if head in runs:
        recorded = runs[head]
        raise RuntimeError(
            f"{base} in {repo} is unchanged since the last digest ({head}): "
            f"{recorded.get('pr_url', '(no url)')}. Refusing to open a duplicate."
        )

    if not args.digest_file.exists():
        raise RuntimeError(f"{args.digest_file} does not exist")
    digest = args.digest_file.read_text()
    if not digest.strip():
        raise RuntimeError(f"{args.digest_file} is empty")

    branch = f"digest/{head}"

    if args.dry_run:
        print(f"target repo: {repo}")
        print(f"would create branch {branch} from {base}")
        print(f"would prepend {len(digest.splitlines())} lines to {changelog}")
        print(f"would open a PR against {base} and record {head} in {STATE_PATH}")
        return 0

    require_clean_tree(repo)
    original = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).strip()

    try:
        run(["git", "checkout", "-b", branch, base], cwd=repo)
        prepend_changelog(changelog, digest)
        run(["git", "add", changelog.name], cwd=repo)
        run(["git", "commit", "-m", f"docs: repo digest through {head}"], cwd=repo)
        run(["git", "push", "-u", "origin", branch], cwd=repo)
        pr_url = run([
            "gh", "pr", "create",
            "--base", base,
            "--head", branch,
            "--title", f"Repo digest through {head}",
            "--body", digest,
        ], cwd=repo).strip().splitlines()[-1]
    finally:
        run(["git", "checkout", original], cwd=repo)

    runs[head] = {
        "pr_url": pr_url,
        "status": "opened",
        "branch": branch,
        "base": base,
        "opened_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    state["active_run"] = None
    save_state(state)

    print(pr_url)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
