"""
CONTEXT.md Auto-Update Script — SP-005

Extracts recent git activity and task board status to keep CONTEXT.md current.
Run manually or via CI before each deploy:

    python scripts/update_context.py

This script is intentionally simple (no external deps) to ensure it runs
everywhere.
"""

import os
import re
import subprocess
from datetime import datetime, timezone


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONTEXT_PATH = os.path.join(REPO_ROOT, "CONTEXT.md")


def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_recent_commits(n: int = 10) -> list[dict]:
    """Return last n commits as {hash, date, message}."""
    fmt = "%H|%ci|%s"
    out = _run_git(["log", f"--format={fmt}", f"-{n}"])
    commits = []
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({"hash": parts[0][:7], "date": parts[1][:10], "message": parts[2]})
    return commits


def get_task_board_summary() -> str:
    """Parse TASK_BOARD.md for active and recently done tasks."""
    tb_path = os.path.join(REPO_ROOT, "TASK_BOARD.md")
    if not os.path.exists(tb_path):
        return "TASK_BOARD.md not found."
    with open(tb_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    active = []
    done = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ] **") or stripped.startswith("- **TASK-"):
            active.append(stripped)
        elif stripped.startswith("- [x] **"):
            done.append(stripped)
    summary = f"Active tasks: {len(active)}\nRecently done: {len(done)}\n"
    if active:
        summary += "\nTop active:\n" + "\n".join(active[:5])
    return summary


def update_context_md() -> None:
    if not os.path.exists(CONTEXT_PATH):
        print(f"ERROR: {CONTEXT_PATH} not found.")
        return

    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Update Last Updated timestamp
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = re.sub(
        r"\*\*Last Updated:\*\* .*",
        f"**Last Updated:** {now} (auto-update script)",
        content,
    )

    # Update Recent Commits block
    commits = get_recent_commits(8)
    commits_md = "\n".join(f"- `{c['hash']}` ({c['date']}) {c['message']}" for c in commits)
    content = re.sub(
        r"(<!-- AUTO:COMMITS_START -->).*?(<!-- AUTO:COMMITS_END -->)",
        f"\\1\n{commits_md}\n\\2",
        content,
        flags=re.DOTALL,
    )

    # Update Task Board block
    tasks_md = get_task_board_summary()
    content = re.sub(
        r"(<!-- AUTO:TASKS_START -->).*?(<!-- AUTO:TASKS_END -->)",
        f"\\1\n{tasks_md}\n\\2",
        content,
        flags=re.DOTALL,
    )

    with open(CONTEXT_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"CONTEXT.md updated at {now}")


if __name__ == "__main__":
    update_context_md()
