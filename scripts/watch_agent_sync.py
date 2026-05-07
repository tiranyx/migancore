#!/usr/bin/env python3
"""
MiganCore Agent Sync Watcher — "ping bash"
Watches docs/AGENT_SYNC/ and alerts when any agent writes a new file.

Usage:
  python scripts/watch_agent_sync.py          # watch + alert in terminal
  python scripts/watch_agent_sync.py --win    # also pop Windows notification

Run this in a separate terminal window. Leave it running all day.
It will ping you when Claude, Kimi, or Codex drops a new file.
"""

import os
import sys
import time
import glob
import subprocess
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WATCH_DIR = REPO_ROOT / "docs" / "AGENT_SYNC"
POLL_INTERVAL = 10  # seconds

WIN_NOTIFY = "--win" in sys.argv

ROLE_MAP = {
    "CLAUDE_PLAN": ("CLAUDE", ">> Kimi: baca dan tulis KIMI_REVIEW_*.md"),
    "KIMI_REVIEW": ("KIMI",   ">> Codex: baca CLAUDE_PLAN + KIMI_REVIEW, tulis CODEX_QA_*.md"),
    "CODEX_QA":   ("CODEX",  ">> Claude: baca Kimi + Codex, jalankan: python tracker.py agent-recap"),
    "RECAP":      ("CLAUDE",  ">> Semua: cycle selesai. Cek RECAP_*.md"),
    "DAY_":       ("CLAUDE",  ">> EOD wrap tersedia. Cek dan commit."),
}


def _detect_role(filename: str):
    for prefix, (agent, action) in ROLE_MAP.items():
        if filename.startswith(prefix):
            return agent, action
    return "UNKNOWN", ">> Cek file baru di AGENT_SYNC/"


def _win_notify(title: str, msg: str):
    """Show Windows toast via PowerShell (no extra pip needed)."""
    try:
        script = (
            f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;"
            f"[System.Windows.Forms.MessageBox]::Show('{msg}', '{title}', 0, 64)"
        )
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", script],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        )
    except Exception:
        pass  # fail silently — terminal alert is primary


def _alert(filename: str, agent: str, action: str):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    sep = "=" * 60
    msg = f"""
{sep}
  [AGENT SYNC PING]  {now}
  Agent : {agent}
  File  : {filename}
  {action}
{sep}
"""
    print(msg, flush=True)

    # Try Windows bell
    print("\a", end="", flush=True)

    if WIN_NOTIFY:
        _win_notify(
            f"[{agent}] AGENT SYNC",
            f"{filename}\n{action}"
        )


def main():
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[WATCHER] Watching: {WATCH_DIR}")
    print(f"[WATCHER] Poll interval: {POLL_INTERVAL}s  |  Win notify: {WIN_NOTIFY}")
    print(f"[WATCHER] Press Ctrl+C to stop.\n")

    seen = set(f.name for f in WATCH_DIR.glob("*.md"))
    print(f"[WATCHER] {len(seen)} existing files (ignored).")

    while True:
        try:
            time.sleep(POLL_INTERVAL)
            current = set(f.name for f in WATCH_DIR.glob("*.md"))
            new_files = current - seen
            for fname in sorted(new_files):
                agent, action = _detect_role(fname)
                _alert(fname, agent, action)
            seen = current
        except KeyboardInterrupt:
            print("\n[WATCHER] Stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"[WATCHER] Error: {e}")


if __name__ == "__main__":
    main()
