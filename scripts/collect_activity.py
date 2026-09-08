#!/usr/bin/env python3
"""Collect a slice of activity from a target repository, as JSON.

Deterministic half of the `repo-digest` workflow: given a repository and a
starting point, print exactly what has happened since. No judgment, no prose,
no network calls beyond `gh`. Read-only — it never writes to the target.

    python3 scripts/collect_activity.py --repo ~/code/my-project
    python3 scripts/collect_activity.py --repo ~/code/my-project --since 2026-08-01
    python3 scripts/collect_activity.py --repo ~/code/my-project --since v1.4.0
    python3 scripts/collect_activity.py --repo ~/code/my-project --since a1b2c3d

`--repo` is the project being digested, somewhere else on your machine — not
this workflow repo. Stdlib only. Requires `git`; `gh` is optional (issues are
omitted without it).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DEFAULT_LOOKBACK_DAYS = 7
TOOL_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path) -> str:
    """Run a command in `cwd`, returning stdout. Raises on failure — never falls back."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed ({proc.returncode}): {proc.stderr.strip()}")
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


def resolve_since(spec: str, repo: Path) -> tuple[list[str], dt.datetime]:
    """Resolve a starting point to (git log args, cutoff timestamp).

    A `YYYY-MM-DD` string is a date. Anything else must be a commit, tag, or
    branch — its committer date becomes the cutoff for issues.
    """
    if ISO_DATE.match(spec):
        cutoff = dt.datetime.fromisoformat(spec).replace(tzinfo=dt.timezone.utc)
        return [f"--since={spec}"], cutoff

    try:
        stamp = run(["git", "log", "-1", "--format=%cI", spec], cwd=repo).strip()
    except RuntimeError as exc:
        raise SystemExit(
            f"Bad --since value {spec!r}; use a YYYY-MM-DD date or a commit/tag/branch.\n{exc}"
        ) from exc
    return [f"{spec}..HEAD"], dt.datetime.fromisoformat(stamp)


def collect_commits(log_args: list[str], repo: Path) -> list[dict]:
    """Commits in the range, excluding merge commits."""
    sep = "\x1f"
    fmt = sep.join(["%H", "%an", "%aI", "%s", "%b"]) + "\x1e"
    raw = run(["git", "log", *log_args, "--no-merges", f"--pretty=format:{fmt}"], cwd=repo)

    commits = []
    for record in raw.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, author, date, subject, body = record.split(sep)
        commits.append({
            "sha": sha[:12],
            "author": author,
            "date": date,
            "subject": subject,
            "body": body.strip(),
            "files": files_touched(sha, repo),
        })
    return commits


def files_touched(sha: str, repo: Path) -> list[str]:
    out = run(["git", "show", "--name-only", "--pretty=format:", sha], cwd=repo)
    return [line for line in out.splitlines() if line.strip()]


def collect_issues(cutoff: dt.datetime, repo: Path) -> list[dict]:
    """Issues closed since the cutoff, via `gh`. Returns [] if gh is unavailable."""
    try:
        raw = run([
            "gh", "issue", "list",
            "--state", "closed",
            "--limit", "200",
            "--json", "number,title,closedAt,labels,url",
        ], cwd=repo)
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"warning: skipping issues ({exc})", file=sys.stderr)
        return []

    issues = []
    for issue in json.loads(raw or "[]"):
        closed = dt.datetime.fromisoformat(issue["closedAt"].replace("Z", "+00:00"))
        if closed >= cutoff:
            issues.append({
                "number": issue["number"],
                "title": issue["title"],
                "closed_at": issue["closedAt"],
                "labels": [label["name"] for label in issue["labels"]],
                "url": issue["url"],
            })
    return sorted(issues, key=lambda i: i["number"])


def main() -> int:
    default_since = (dt.date.today() - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS)).isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="path to the repository being digested")
    parser.add_argument(
        "--since",
        default=default_since,
        help=f"a YYYY-MM-DD date or a commit/tag/branch (default: {DEFAULT_LOOKBACK_DAYS} days ago)",
    )
    args = parser.parse_args()

    repo = resolve_repo(args.repo)
    log_args, cutoff = resolve_since(args.since, repo)
    commits = collect_commits(log_args, repo)
    issues = collect_issues(cutoff, repo)
    head = run(["git", "rev-parse", "--short", "HEAD"], cwd=repo).strip()

    json.dump(
        {
            "repo": str(repo),
            "since": {"spec": args.since, "cutoff": cutoff.isoformat()},
            "head": head,
            "commits": commits,
            "issues": issues,
            "stats": {
                "commit_count": len(commits),
                "issue_count": len(issues),
                "authors": sorted({c["author"] for c in commits}),
            },
        },
        sys.stdout,
        indent=2,
    )
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
