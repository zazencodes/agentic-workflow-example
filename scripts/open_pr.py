#!/usr/bin/env python3
"""Open the weekly-digest pull request.

Deterministic other half of the `weekly-digest` workflow: take an approved
digest and turn it into a branch, a commit, and a PR — the same way every time.

    python3 scripts/open_pr.py --week 2026-W36 --digest-file /tmp/digest.md

This is the only irreversible step in the workflow. It runs only after the
Step 3 approval gate. Stdlib only; requires `git` and an authenticated `gh`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO_ROOT / "state" / "digest-index.json"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"


def run(cmd: list[str], capture: bool = True) -> str:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=capture, text=True)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"{' '.join(cmd)} failed ({proc.returncode}): {stderr}")
    return proc.stdout if capture else ""


def load_index() -> dict:
    if not INDEX_PATH.exists():
        return {"weeks": {}}
    return json.loads(INDEX_PATH.read_text())


def save_index(index: dict) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n")


def require_clean_tree() -> None:
    if run(["git", "status", "--porcelain"]).strip():
        raise RuntimeError("working tree is not clean; commit or stash first")


def prepend_changelog(digest: str) -> None:
    existing = CHANGELOG_PATH.read_text() if CHANGELOG_PATH.exists() else "# Changelog\n"
    header, _, body = existing.partition("\n")
    CHANGELOG_PATH.write_text(f"{header}\n\n{digest.strip()}\n{body}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", required=True, help="ISO week label, e.g. 2026-W36")
    parser.add_argument("--digest-file", required=True, type=Path)
    parser.add_argument("--base", default="main", help="base branch (default: main)")
    parser.add_argument("--dry-run", action="store_true", help="show the plan, change nothing")
    args = parser.parse_args()

    index = load_index()
    if args.week in index["weeks"]:
        recorded = index["weeks"][args.week]
        raise RuntimeError(
            f"{args.week} already digested: {recorded.get('pr_url', '(no url)')}. "
            "Refusing to open a duplicate."
        )

    digest = args.digest_file.read_text()
    if not digest.strip():
        raise RuntimeError(f"{args.digest_file} is empty")

    branch = f"digest/{args.week}"
    original = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()

    if args.dry_run:
        print(f"would create branch {branch} from {args.base}")
        print(f"would prepend {len(digest.splitlines())} lines to {CHANGELOG_PATH.name}")
        print(f"would open a PR against {args.base} and record {args.week} in the index")
        return 0

    require_clean_tree()

    try:
        run(["git", "checkout", "-b", branch, args.base])
        prepend_changelog(digest)
        run(["git", "add", str(CHANGELOG_PATH.relative_to(REPO_ROOT))])
        run(["git", "commit", "-m", f"docs: weekly digest for {args.week}"])
        run(["git", "push", "-u", "origin", branch])
        pr_url = run([
            "gh", "pr", "create",
            "--base", args.base,
            "--head", branch,
            "--title", f"Weekly digest: {args.week}",
            "--body", digest,
        ]).strip().splitlines()[-1]
    finally:
        run(["git", "checkout", original])

    index["weeks"][args.week] = {"pr_url": pr_url, "status": "opened", "branch": branch}
    save_index(index)

    print(pr_url)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
