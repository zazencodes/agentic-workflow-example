#!/usr/bin/env python3
"""Collect one ISO week of repository activity as JSON.

Deterministic half of the `weekly-digest` workflow: given a week, print exactly
what happened in it. No judgment, no prose, no network calls beyond `gh`.

    python3 scripts/collect_activity.py --week last
    python3 scripts/collect_activity.py --week 2026-W36

Stdlib only. Requires `git`; `gh` is optional (issues are omitted without it).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys


def run(cmd: list[str]) -> str:
    """Run a command, returning stdout. Raises on failure — never falls back."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def week_bounds(week: str) -> tuple[str, dt.date, dt.date]:
    """Resolve a week spec to (label, monday, sunday)."""
    if week == "last":
        today = dt.date.today()
        monday = today - dt.timedelta(days=today.weekday() + 7)
    else:
        try:
            year, num = week.split("-W")
            monday = dt.date.fromisocalendar(int(year), int(num), 1)
        except ValueError as exc:
            raise SystemExit(f"Bad --week value {week!r}; use 'last' or '2026-W36'") from exc

    iso = monday.isocalendar()
    return f"{iso.year}-W{iso.week:02d}", monday, monday + dt.timedelta(days=6)


def collect_commits(since: dt.date, until: dt.date) -> list[dict]:
    """Commits authored in [since, until], excluding merge commits."""
    sep = "\x1f"
    fmt = sep.join(["%H", "%an", "%aI", "%s", "%b"]) + "\x1e"
    raw = run([
        "git", "log",
        f"--since={since.isoformat()}",
        f"--until={(until + dt.timedelta(days=1)).isoformat()}",
        "--no-merges",
        f"--pretty=format:{fmt}",
    ])

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
            "files": files_touched(sha),
        })
    return commits


def files_touched(sha: str) -> list[str]:
    out = run(["git", "show", "--name-only", "--pretty=format:", sha])
    return [line for line in out.splitlines() if line.strip()]


def collect_issues(since: dt.date, until: dt.date) -> list[dict]:
    """Issues closed in the window, via `gh`. Returns [] if gh is unavailable."""
    try:
        raw = run([
            "gh", "issue", "list",
            "--state", "closed",
            "--limit", "200",
            "--json", "number,title,closedAt,labels,url",
        ])
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"warning: skipping issues ({exc})", file=sys.stderr)
        return []

    issues = []
    for issue in json.loads(raw or "[]"):
        closed = dt.datetime.fromisoformat(issue["closedAt"].replace("Z", "+00:00")).date()
        if since <= closed <= until:
            issues.append({
                "number": issue["number"],
                "title": issue["title"],
                "closed_at": issue["closedAt"],
                "labels": [label["name"] for label in issue["labels"]],
                "url": issue["url"],
            })
    return sorted(issues, key=lambda i: i["number"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", default="last", help="'last' or an ISO week like 2026-W36")
    args = parser.parse_args()

    label, monday, sunday = week_bounds(args.week)
    commits = collect_commits(monday, sunday)
    issues = collect_issues(monday, sunday)

    json.dump(
        {
            "week": label,
            "range": {"from": monday.isoformat(), "to": sunday.isoformat()},
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
