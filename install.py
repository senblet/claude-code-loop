#!/usr/bin/env python3
"""Install the Architect -> Builders -> Reviewer loop into a project.

Copies the three agent definitions and the /ship command into a project's
`.claude/`, then checks the one thing that breaks this setup silently: a
.gitignore that swallows `.claude/` or `.claude/agent-memory/`. Ignored agent
files are not shared with anyone; ignored memory means the loop relearns the
same lessons on every machine.

Standard library only, no dependencies.

    python3 install.py [target]        install into target (default: cwd)
    python3 install.py --dry-run       show what would happen, change nothing
    python3 install.py --force         overwrite files that differ
    python3 install.py --commit        also stage and commit .claude/
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent

# source path -> path relative to the project root
FILES = {
    "agents/architect.md": ".claude/agents/architect.md",
    "agents/builder.md": ".claude/agents/builder.md",
    "agents/reviewer.md": ".claude/agents/reviewer.md",
    "commands/ship.md": ".claude/commands/ship.md",
}

# `plans` is where the Architect writes; the agents create their own memory
# directories at runtime, so this script only checks that git can see them.
DIRS = [".claude/agents", ".claude/commands", ".claude/plans"]
MEMORY = ".claude/agent-memory"


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )


def is_repo(root: Path) -> bool:
    return git(root, "rev-parse", "--is-inside-work-tree").returncode == 0


def is_ignored(root: Path, relative: str) -> bool:
    """True if git would ignore this path. Works on paths that do not exist yet."""
    return git(root, "check-ignore", "-q", relative).returncode == 0


def plan_file(source: Path, destination: Path, force: bool) -> str:
    """Decide what to do with one file, without touching the disk."""
    if not destination.exists():
        return "install"
    if filecmp.cmp(source, destination, shallow=False):
        return "unchanged"
    return "overwrite" if force else "skip"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", nargs="?", default=".", help="project root")
    parser.add_argument("--force", action="store_true", help="overwrite files that differ")
    parser.add_argument("--dry-run", action="store_true", help="change nothing")
    parser.add_argument("--commit", action="store_true", help="stage and commit .claude/")
    args = parser.parse_args()

    root = Path(args.target).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1
    if root == SOURCE:
        print("error: that is the template itself. Pass the project to install into.",
              file=sys.stderr)
        return 1

    actions = {name: plan_file(SOURCE / name, root / dest, args.force)
               for name, dest in FILES.items()}

    print(f"{'would install' if args.dry_run else 'installing'} into {root}\n")

    if not args.dry_run:
        for directory in DIRS:
            (root / directory).mkdir(parents=True, exist_ok=True)

    marks = {"install": "+", "overwrite": "~", "unchanged": "=", "skip": "!"}
    for name, dest in FILES.items():
        action = actions[name]
        if action in ("install", "overwrite") and not args.dry_run:
            shutil.copy2(SOURCE / name, root / dest)
        note = " (differs — use --force to overwrite)" if action == "skip" else ""
        print(f"  {marks[action]} {dest}{note}")

    skipped = [n for n, a in actions.items() if a == "skip"]
    warnings = []

    if is_repo(root):
        if is_ignored(root, ".claude/agents/architect.md"):
            warnings.append(
                ".gitignore hides .claude/ — the agents are installed but untracked,\n"
                "    so nobody else on this repo gets them. Unignore .claude/agents/\n"
                "    and .claude/commands/."
            )
        elif is_ignored(root, f"{MEMORY}/builder/MEMORY.md"):
            warnings.append(
                f".gitignore hides {MEMORY}/ — the loop will relearn the same\n"
                "    lessons on every machine. Commit that directory or the learning\n"
                "    mechanism is decorative."
            )
    else:
        warnings.append(
            "not a git repository, so nothing here is tracked. The Reviewer diffs\n"
            "    against a base commit and /ship opens a PR; both need git."
        )

    for warning in warnings:
        print(f"\n  warning: {warning}")

    if args.dry_run:
        print("\ndry run — nothing was written.")
        return 0

    if args.commit and is_repo(root):
        git(root, "add", ".claude")
        staged = git(root, "diff", "--cached", "--quiet", "--", ".claude").returncode != 0
        if staged:
            git(root, "commit", "-m", "chore: install agent loop")
            print("\ncommitted .claude/")
        else:
            print("\nnothing to commit.")

    print("\nRestart Claude Code — a running session does not pick up a newly")
    print("created agents/ directory. Then type / and look for `ship`.")

    if skipped:
        print(f"\n{len(skipped)} file(s) left alone because they differ from the template.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
