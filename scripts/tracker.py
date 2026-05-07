#!/usr/bin/env python3
"""
MiganCore Tracker CLI — Living System State Manager
Version: 1.0 · Day 69 · 2026-05-08

Usage:
  python scripts/tracker.py status                     Show current system state (git + API)
  python scripts/tracker.py day-start N [--topic T]   Generate pre-execution brief for day N
  python scripts/tracker.py day-end N                 Generate end-of-day wrap template
  python scripts/tracker.py agent-sync TOPIC [--day N] Generate Claude execution plan for agents
  python scripts/tracker.py agent-read kimi --day N --topic T  Read Kimi review
  python scripts/tracker.py agent-recap --day N --topic T      Generate final recap from all reviews
  python scripts/tracker.py backlog                    Show prioritized backlog from TRACKER
  python scripts/tracker.py lesson "TEXT" [--day N]   Append lesson to TRACKER + AGENT_ONBOARDING
  python scripts/tracker.py align                     Show vision alignment map
  python scripts/tracker.py update                    Update QUICK_STATUS block in TRACKER

All plan/review/recap files go to: docs/AGENT_SYNC/
Tracker file: docs/MIGANCORE_TRACKER.md
"""

import argparse
import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
import datetime
import re
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
TRACKER = REPO_ROOT / "docs" / "MIGANCORE_TRACKER.md"
AGENT_SYNC_DIR = REPO_ROOT / "docs" / "AGENT_SYNC"
ONBOARDING = REPO_ROOT / "AGENT_ONBOARDING.md"

API_LOCAL = "http://localhost:18000"
API_PUBLIC = "https://api.migancore.com"

# ── Helpers ────────────────────────────────────────────────────────────────────
def _git(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git"] + cmd, cwd=REPO_ROOT, stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
    except Exception:
        return ""


def _fetch_health(base: str, timeout: int = 5) -> dict | None:
    try:
        req = urllib.request.Request(f"{base}/health")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _fetch_ready(base: str, timeout: int = 5) -> dict | None:
    try:
        req = urllib.request.Request(f"{base}/ready")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _ensure_sync_dir():
    AGENT_SYNC_DIR.mkdir(parents=True, exist_ok=True)
    gitignore = AGENT_SYNC_DIR / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("# AGENT_SYNC files tracked in git — do not ignore\n")


def _topic_slug(topic: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", topic.upper())[:30]


def _read_tracker_section(tag: str) -> str:
    """Read content between <!-- Section tag: TAG --> markers."""
    text = TRACKER.read_text(encoding="utf-8")
    pattern = rf"<!-- Section tag: {re.escape(tag)} -->(.*?)(?=\n---|\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _update_tracker_block(start_marker: str, end_marker: str, new_content: str):
    """Replace content between two markers in TRACKER."""
    text = TRACKER.read_text(encoding="utf-8")
    pattern = rf"({re.escape(start_marker)})(.*?)({re.escape(end_marker)})"
    replacement = rf"\1\n{new_content}\n\3"
    new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
    if count == 0:
        print(f"⚠️  Marker not found: {start_marker}")
        return False
    TRACKER.write_text(new_text, encoding="utf-8")
    return True


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_status(args):
    """Show current system state."""
    print("=" * 60)
    print("  MIGANCORE SYSTEM STATUS")
    print(f"  {_today()}")
    print("=" * 60)

    # Git
    sha = _git(["rev-parse", "--short", "HEAD"])
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    dirty = _git(["status", "--porcelain"])
    ahead = _git(["rev-list", "--count", "HEAD..origin/main"]) or "?"
    behind = _git(["rev-list", "--count", "origin/main..HEAD"]) or "?"
    recent = _git(["log", "--oneline", "-5"])

    print("\n[GIT]")
    print(f"  Branch : {branch}")
    print(f"  SHA    : {sha}")
    print(f"  Dirty  : {'YES -- uncommitted changes' if dirty else 'clean'}")
    print(f"  Status : {ahead} ahead / {behind} behind origin/main")
    print("\n  Recent commits:")
    for line in recent.splitlines():
        print(f"    {line}")

    # API — try local first
    print("\n[API]")
    health = _fetch_health(API_LOCAL) or _fetch_health(API_PUBLIC)
    ready = _fetch_ready(API_LOCAL) or _fetch_ready(API_PUBLIC)

    if health:
        endpoint = "localhost:18000" if _fetch_health(API_LOCAL) else "api.migancore.com"
        print(f"  Endpoint   : {endpoint}")
        print(f"  Status     : {health.get('status', '?')}")
        print(f"  Version    : {health.get('version', '?')}")
        print(f"  Model      : {health.get('model', '?')}")
        print(f"  Commit SHA : {health.get('commit_sha', '?')}")
        print(f"  Build time : {health.get('build_time', '?')}")
        print(f"  Build day  : {health.get('day', '?')}")

        # SHA drift check
        if sha and health.get("commit_sha") and sha != health.get("commit_sha"):
            print(f"\n  !! DRIFT DETECTED: local={sha} vs API={health.get('commit_sha')}")
            print(f"     Run: BUILD_COMMIT_SHA={sha} docker compose up -d api")
        elif sha and health.get("commit_sha"):
            print(f"\n  OK No drift: local SHA matches API")
    else:
        print("  FAIL: API unreachable (tried local + public)")

    if ready:
        print("\n[DOWNSTREAM SERVICES]")
        # /ready returns {status: "ready", checks: {postgres: {status:ok}, ...}} or flat dict
        checks = ready.get("checks", ready)
        overall = ready.get("status", "?")
        print(f"  Overall: {overall}")
        for svc, info in checks.items():
            if isinstance(info, dict):
                s = info.get("status", "?")
                detail = info.get("detail", "")
                icon = "OK" if s == "ok" else "FAIL"
                print(f"  [{icon}] {svc}: {s} — {detail}")
            else:
                icon = "OK" if "ok" in str(info).lower() or info is True else "FAIL"
                print(f"  [{icon}] {svc}: {info}")

    # TRACKER quick reference
    print("\n[TRACKER]")
    print(f"  File: {TRACKER}")
    print(f"  Agent sync dir: {AGENT_SYNC_DIR}")
    if AGENT_SYNC_DIR.exists():
        files = list(AGENT_SYNC_DIR.glob("*.md"))
        print(f"  Agent sync files: {len(files)}")
        for f in sorted(files)[-5:]:
            print(f"    {f.name}")
    print()


def cmd_day_start(args):
    """Generate pre-execution research brief for a day."""
    day = args.day
    topic = args.topic or "general"
    slug = _topic_slug(topic)
    now = _today()

    sha = _git(["rev-parse", "--short", "HEAD"])
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    recent = _git(["log", "--oneline", "-3"])
    health = _fetch_health(API_LOCAL) or _fetch_health(API_PUBLIC)

    model = health.get("model", "unknown") if health else "unknown"
    api_sha = health.get("commit_sha", "unknown") if health else "unknown"
    api_status = health.get("status", "unreachable") if health else "unreachable"

    template = f"""# DAY {day} — PRE-EXECUTION BRIEF
**Date:** {now}
**Topic:** {topic}
**Generated by:** python scripts/tracker.py day-start {day} --topic "{topic}"

---

## SYSTEM STATE SNAPSHOT

| Key | Value |
|-----|-------|
| Git SHA (local) | `{sha}` |
| Branch | `{branch}` |
| API SHA | `{api_sha}` |
| SHA drift | {'YES ⚠️' if sha != api_sha else 'NO ✅'} |
| Production brain | `{model}` |
| API status | {api_status} |

**Recent commits:**
```
{recent}
```

---

## OBJECTIVES FOR TODAY

<!-- Fill in before execution starts -->

### P0 (Must ship)
1.
2.

### P1 (Should ship)
1.
2.

### P2 (Nice to have)
1.

---

## HYPOTHESIS

<!-- What do you believe will work, and why? -->

**IF** we [do X]
**THEN** [Y will happen]
**BECAUSE** [Z mechanism]

**Confidence:** Low / Medium / High
**Evidence supporting:**
**Evidence against:**

---

## RISK / BENEFIT / IMPACT

| Dimension | Assessment |
|-----------|------------|
| **Risk** | (What could break?) |
| **Benefit** | (What do we gain if it works?) |
| **Impact** | (Who/what is affected?) |
| **Reversibility** | (Can we roll back? How quickly?) |
| **Cost** | (Compute, time, complexity) |

---

## PRE-EXECUTION CHECKLIST

- [ ] 5-layer alignment: local SHA = server SHA = API SHA
- [ ] No dirty git state (or changes are intentional)
- [ ] Rollback plan defined
- [ ] Not touching: synthetic gen, tools stack (unless on roadmap)
- [ ] Admin key: NOT in any doc file
- [ ] If training: Vast.ai pod — set timeout, verify DELETE, check cost
- [ ] If deploy: use `BUILD_COMMIT_SHA` pattern + smoke test after

---

## RESEARCH QUESTIONS FOR KIMI

<!-- 3-5 specific questions for Kimi to research before Claude executes -->

1.
2.
3.

---

## DECISION GATE

**GO if:**
-
-

**NO-GO if:**
-
-

**Fallback plan:**


---

## AGENT SYNC

This file → `docs/AGENT_SYNC/CLAUDE_PLAN_{day}_{slug}.md`

Kimi: please read and write response to `KIMI_REVIEW_{day}_{slug}.md`
Codex: please read CLAUDE_PLAN + KIMI_REVIEW and write `CODEX_QA_{day}_{slug}.md`
"""

    _ensure_sync_dir()
    out_file = AGENT_SYNC_DIR / f"CLAUDE_PLAN_{day}_{slug}.md"
    out_file.write_text(template, encoding="utf-8")
    print(f"✅ Pre-execution brief created: {out_file}")
    print(f"   For Kimi in VS Code: code \"{out_file}\"")
    print(f"   Kimi writes response to: AGENT_SYNC/KIMI_REVIEW_{day}_{slug}.md")


def cmd_day_end(args):
    """Generate end-of-day wrap template."""
    day = args.day
    now = _today()

    sha = _git(["rev-parse", "--short", "HEAD"])
    health = _fetch_health(API_LOCAL) or _fetch_health(API_PUBLIC)
    model = health.get("model", "unknown") if health else "unknown"
    api_sha = health.get("commit_sha", "unknown") if health else "unknown"
    recent = _git(["log", "--oneline", "-5"])

    # Count new commits since start of day (approximate)
    today_commits = _git(["log", "--oneline", "--since=00:00", "--format=%h %s"])

    template = f"""# DAY {day} — END-OF-DAY WRAP
**Date:** {now}
**Generated by:** python scripts/tracker.py day-end {day}

---

## DELIVERY SUMMARY

### ✅ Completed
- [ ] (fill in)

### ⚠️ Partial
- [ ] (fill in)

### ❌ Not done (carry to Day {day+1})
- [ ] (fill in)

---

## SEAMLESS AUDIT — 5 LAYERS

| Layer | Commit | Status |
|-------|--------|--------|
| 1. Local repo | `{sha}` | [verify: git status -sb] |
| 2. GitHub (origin/main) | `{sha}` | [verify: git log --oneline -1 origin/main] |
| 3. Server (/opt/ado) | | [verify: ssh → git log -1 --oneline] |
| 4. API container | `{api_sha}` | [verify: curl /health → commit_sha] |
| 5. Live frontend | | [verify: curl -I app.migancore.com] |

**Drift:** {'DETECTED ⚠️' if sha != api_sha else 'None ✅'}

---

## STATE CHANGES

**Production brain:** `{model}`
**Commits today:**
```
{today_commits or recent}
```

**DB state:** (total pairs, feedback signals, user count — paste from admin stats)

---

## LESSONS LEARNED

<!-- Add each lesson. Will be appended to tracker with: python tracker.py lesson "TEXT" -->

| # | Category | Lesson |
|---|----------|--------|
| NEW | Workflow | |
| NEW | Infrastructure | |
| NEW | Training | |

---

## HYPOTHESIS VERDICT

**What we hypothesized:**
**What actually happened:**
**Why the delta:**
**Update mental model:**

---

## COSTS

| Item | Cost | Notes |
|------|------|-------|
| Vast.ai | $ | Instance ID: |
| Other | $ | |
| **Total Day {day}** | **$** | |

---

## NEXT DAY PRIORITIES (Day {day+1})

### P0
1.

### P1
1.

### Agent handoff
- Kimi:
- Codex:

---

## MANDATORY PROTOCOL

- [ ] Committed all changes to main
- [ ] Pushed to GitHub
- [ ] Server synced (git pull on VPS)
- [ ] Lesson(s) appended to AGENT_ONBOARDING.md
- [ ] MIGANCORE_TRACKER.md updated (day log entry, backlog status)
- [ ] DAY{day}_PROGRESS.md written (or this file committed as equivalent)
"""

    _ensure_sync_dir()
    out_file = AGENT_SYNC_DIR / f"DAY_{day}_EOD_WRAP.md"
    out_file.write_text(template, encoding="utf-8")
    print(f"✅ End-of-day wrap created: {out_file}")
    print(f"   Fill in and commit as part of Day {day} close.")


def cmd_agent_sync(args):
    """Generate Claude execution plan file for agent coordination."""
    topic = args.topic
    day = args.day or _infer_day()
    slug = _topic_slug(topic)

    sha = _git(["rev-parse", "--short", "HEAD"])
    health = _fetch_health(API_LOCAL) or _fetch_health(API_PUBLIC)
    model = health.get("model", "unknown") if health else "unknown"
    api_sha = health.get("commit_sha", "unknown") if health else "unknown"
    now = _today()

    plan_file = AGENT_SYNC_DIR / f"CLAUDE_PLAN_{day}_{slug}.md"
    kimi_file = AGENT_SYNC_DIR / f"KIMI_REVIEW_{day}_{slug}.md"
    codex_file = AGENT_SYNC_DIR / f"CODEX_QA_{day}_{slug}.md"
    recap_file = AGENT_SYNC_DIR / f"RECAP_{day}_{slug}.md"

    template = f"""# CLAUDE EXECUTION PLAN — Day {day}: {topic}
**Generated:** {now}
**Status:** DRAFT → awaiting KIMI_REVIEW + CODEX_QA

Files in this exchange:
- This file: `CLAUDE_PLAN_{day}_{slug}.md` (Claude writes)
- Kimi writes: `KIMI_REVIEW_{day}_{slug}.md`
- Codex writes: `CODEX_QA_{day}_{slug}.md`
- Claude recap: `RECAP_{day}_{slug}.md`

---

## CONTEXT

| Key | Value |
|-----|-------|
| Day | {day} |
| Local SHA | `{sha}` |
| API SHA | `{api_sha}` |
| Production Brain | `{model}` |
| Topic | {topic} |

---

## OBJECTIVE

<!-- What we are trying to accomplish, and why now -->


---

## EXECUTION PLAN

<!-- Step-by-step. Each step must have a rollback. -->

### Step 1 — [Name]
**Action:**
**Files changed:**
**Rollback:** `git revert HEAD` / restart previous container

### Step 2 — [Name]
**Action:**
**Files changed:**
**Rollback:**

---

## HYPOTHESIS

**IF** we [do X]
**THEN** [Y]
**BECAUSE** [Z]

**Confidence:** Low / Medium / High

---

## RISK / BENEFIT / IMPACT

| Dimension | Detail |
|-----------|--------|
| Risk | |
| Benefit | |
| Impact | |
| Reversibility | |
| Cost | |

---

## RESEARCH QUESTIONS FOR KIMI

1.
2.
3.

---

## DECISION GATE

**GO if:**
-

**NO-GO if:**
-

---

<!-- Kimi: please fill KIMI_REVIEW_{day}_{slug}.md using template below -->
<!-- Kimi template:
## VERDICT: GO / NO-GO / CONDITIONAL

## RESEARCH FINDINGS

## ANALYSIS

## RISKS MISSED BY CLAUDE

## RECOMMENDATION
-->

<!-- Codex: please fill CODEX_QA_{day}_{slug}.md using template below -->
<!-- Codex template:
## SECURITY FINDINGS
(Severity: P1/P2/P3, file:line)

## LOGIC BUGS

## MISSING TESTS

## SIGN-OFF: YES / CONDITIONAL / NO
-->
"""

    _ensure_sync_dir()
    plan_file.write_text(template, encoding="utf-8")
    print(f"\n✅ Agent sync created for: {topic}")
    print(f"\n📄 CLAUDE PLAN → {plan_file}")
    print(f"   For Kimi in VS Code: code \"{plan_file}\"")
    print(f"   Kimi writes to:  {kimi_file.name}")
    print(f"   Codex writes to: {codex_file.name}")
    print(f"   Claude recap to: {recap_file.name}")
    print(f"\n▶ Next steps:")
    print(f"  1. Fill in this plan file (objective, steps, research questions)")
    print(f"  2. Share with Kimi in VS Code")
    print(f"  3. Kimi writes KIMI_REVIEW → Claude reads with: python tracker.py agent-read kimi --day {day} --topic \"{topic}\"")
    print(f"  4. Codex writes CODEX_QA → Claude writes recap: python tracker.py agent-recap --day {day} --topic \"{topic}\"")


def cmd_agent_read(args):
    """Read agent review files (Kimi or Codex)."""
    agent = args.agent.lower()
    day = args.day or _infer_day()
    topic = args.topic or "general"
    slug = _topic_slug(topic)

    if agent == "kimi":
        f = AGENT_SYNC_DIR / f"KIMI_REVIEW_{day}_{slug}.md"
    elif agent == "codex":
        f = AGENT_SYNC_DIR / f"CODEX_QA_{day}_{slug}.md"
    else:
        print(f"❌ Unknown agent: {agent}. Use 'kimi' or 'codex'.")
        sys.exit(1)

    if not f.exists():
        print(f"❌ File not found: {f}")
        print(f"   Waiting for {agent.title()} to write it.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  {agent.upper()} REVIEW — Day {day}: {topic}")
    print(f"{'='*60}\n")
    print(f.read_text(encoding="utf-8"))


def cmd_agent_recap(args):
    """Generate final recap from all agent reviews."""
    day = args.day or _infer_day()
    topic = args.topic or "general"
    slug = _topic_slug(topic)
    now = _today()

    plan_f = AGENT_SYNC_DIR / f"CLAUDE_PLAN_{day}_{slug}.md"
    kimi_f = AGENT_SYNC_DIR / f"KIMI_REVIEW_{day}_{slug}.md"
    codex_f = AGENT_SYNC_DIR / f"CODEX_QA_{day}_{slug}.md"
    recap_f = AGENT_SYNC_DIR / f"RECAP_{day}_{slug}.md"

    kimi_exists = kimi_f.exists()
    codex_exists = codex_f.exists()

    if not kimi_exists:
        print(f"⚠️  Kimi review not found: {kimi_f.name}")
    if not codex_exists:
        print(f"⚠️  Codex QA not found: {codex_f.name}")

    sha = _git(["rev-parse", "--short", "HEAD"])
    recent = _git(["log", "--oneline", "-3"])

    template = f"""# RECAP — Day {day}: {topic}
**Date:** {now}
**Author:** Claude (after reading Kimi + Codex)
**Status:** FINAL

---

## INPUT SUMMARY

| Source | File | Status |
|--------|------|--------|
| Claude Plan | CLAUDE_PLAN_{day}_{slug}.md | ✅ |
| Kimi Review | KIMI_REVIEW_{day}_{slug}.md | {'✅' if kimi_exists else '❌ missing'} |
| Codex QA | CODEX_QA_{day}_{slug}.md | {'✅' if codex_exists else '❌ missing'} |

---

## DECISION: GO / NO-GO / CONDITIONAL

**Decision:**
**Rationale:**

---

## WHAT WE BUILT

### Completed
-

### Changed from plan (based on Kimi/Codex feedback)
-

---

## KIMI KEY INSIGHTS
<!-- Summarize most important points from KIMI_REVIEW -->

1.
2.

---

## CODEX FINDINGS ADDRESSED
<!-- List security/logic issues found by Codex and how resolved -->

| Finding | Severity | Resolution |
|---------|----------|------------|
| | | |

---

## HYPOTHESIS VERDICT

**Was hypothesis correct?**
**Why / why not:**

---

## NEW LESSONS
<!-- Use: python tracker.py lesson "TEXT" --day {day} to append each -->

1. #{'{NEXT_NUM}'} · Day {day} · [Category] · [Lesson text]

---

## COMMITS

```
{recent}
```

Local SHA: `{sha}`

---

## NEXT AGENT TASK

**For Kimi:**
**For Codex:**
**For Claude (Day {day+1}):**

---

*Recap complete. Update MIGANCORE_TRACKER.md day log entry.*
"""

    recap_f.write_text(template, encoding="utf-8")
    print(f"✅ Recap template created: {recap_f}")
    print(f"   Fill in and commit.")


def cmd_backlog(args):
    """Show current backlog from TRACKER."""
    if not TRACKER.exists():
        print("❌ TRACKER not found. Run from repo root.")
        sys.exit(1)

    text = TRACKER.read_text(encoding="utf-8")
    # Find backlog section
    m = re.search(r"## 📋 BACKLOG.*?(?=\n## )", text, re.DOTALL)
    if not m:
        print("❌ Backlog section not found in TRACKER.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  BACKLOG — MIGANCORE TRACKER")
    print("=" * 60)
    print(m.group(0))


def cmd_lesson(args):
    """Append a lesson to TRACKER and AGENT_ONBOARDING."""
    lesson_text = args.text
    day = args.day or _infer_day()

    # Get next lesson number from TRACKER
    text = TRACKER.read_text(encoding="utf-8") if TRACKER.exists() else ""
    nums = [int(m) for m in re.findall(r"^\| (\d{2,3}) \|", text, re.MULTILINE)]
    next_num = max(nums) + 1 if nums else 155

    # Prompt for category
    categories = ["Workflow", "Infrastructure", "Training", "Security", "Product", "Tooling", "Architecture", "Performance", "QA"]
    print("Categories:", ", ".join(f"[{i+1}] {c}" for i, c in enumerate(categories)))
    cat_input = input(f"Category number [1-{len(categories)}] or type custom: ").strip()
    try:
        category = categories[int(cat_input) - 1]
    except (ValueError, IndexError):
        category = cat_input or "General"

    new_row = f"| {next_num} | {day} | {category} | {lesson_text} |"
    print(f"\n✅ New lesson: {new_row}")

    # Append to TRACKER after "### Recent Lessons" table
    if TRACKER.exists():
        text = TRACKER.read_text(encoding="utf-8")
        # Find the lessons table header row and insert after last row before next heading
        insert_marker = "| # | Day | Category | Lesson |"
        separator = "|---|-----|----------|--------|"
        if insert_marker in text:
            # Find the table and append row
            idx = text.find(separator, text.find(insert_marker))
            # Find end of table (blank line after separator)
            after_sep = text[idx + len(separator):]
            # Insert new row right after header + separator
            insert_pos = idx + len(separator)
            text = text[:insert_pos] + f"\n{new_row}" + text[insert_pos:]
            TRACKER.write_text(text, encoding="utf-8")
            print(f"   Added to MIGANCORE_TRACKER.md")
        else:
            print(f"   ⚠️ Could not locate lessons table in TRACKER. Add manually.")

    # Also append to AGENT_ONBOARDING if it exists
    if ONBOARDING.exists():
        onboarding_text = ONBOARDING.read_text(encoding="utf-8")
        # Look for lessons section
        append_entry = f"\n### Lesson #{next_num} (Day {day})\n- **Category:** {category}\n- **Lesson:** {lesson_text}\n"
        if "## LESSONS" in onboarding_text or "## Lessons" in onboarding_text:
            # Find end of lessons section or file
            onboarding_text += append_entry
        else:
            onboarding_text += f"\n## Lessons (auto-appended)\n{append_entry}"
        ONBOARDING.write_text(onboarding_text, encoding="utf-8")
        print(f"   Added to AGENT_ONBOARDING.md")

    print(f"\n   Remember to commit: git add docs/MIGANCORE_TRACKER.md AGENT_ONBOARDING.md && git commit -m \"Lesson #{next_num}: {lesson_text[:50]}\"")


def cmd_align(args):
    """Show vision alignment map from TRACKER."""
    if not TRACKER.exists():
        print("❌ TRACKER not found.")
        sys.exit(1)

    text = TRACKER.read_text(encoding="utf-8")
    m = re.search(r"## 🎯 VISION ALIGNMENT MAP.*?(?=\n## )", text, re.DOTALL)
    if not m:
        print("❌ Vision alignment section not found in TRACKER.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  VISION ALIGNMENT — MIGANCORE TRACKER")
    print("=" * 60)
    print(m.group(0))


def cmd_update(args):
    """Update QUICK_STATUS block in TRACKER from live state."""
    sha = _git(["rev-parse", "--short", "HEAD"])
    health = _fetch_health(API_LOCAL) or _fetch_health(API_PUBLIC)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    model = health.get("model", "unknown") if health else "UNREACHABLE"
    api_sha = health.get("commit_sha", "unknown") if health else "unknown"
    api_version = health.get("version", "unknown") if health else "unknown"
    api_day = health.get("day", "unknown") if health else "unknown"
    drift = "⚠️ DRIFT" if sha != api_sha else "✅ aligned"

    new_status = f"""
| Key | Value |
|-----|-------|
| **Updated** | {now} |
| **Git SHA (local)** | `{sha}` |
| **API SHA** | `{api_sha}` |
| **SHA drift** | {drift} |
| **Production Brain** | `{model}` |
| **API Version** | {api_version} ({api_day}) |
| **API Health** | https://api.migancore.com/health |
| **Chat App** | https://app.migancore.com |
"""

    if TRACKER.exists():
        text = TRACKER.read_text(encoding="utf-8")
        # Replace the table after QUICK_STATUS heading
        pattern = r"(## ⚡ QUICK STATUS\n<!-- Section tag: QUICK_STATUS.*?-->)(.*?)(?=\n---|\n## )"
        replacement = rf"\1{new_status}\n"
        new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
        if count > 0:
            TRACKER.write_text(new_text, encoding="utf-8")
            print(f"✅ QUICK_STATUS updated in MIGANCORE_TRACKER.md")
        else:
            print("⚠️  QUICK_STATUS marker not found. Add manually.")

    print(f"\n  Git: {sha} | API: {api_sha} | {drift}")
    print(f"  Brain: {model}")


def _infer_day() -> int:
    """Infer current day from today's date. Day 1 = 2026-03-05."""
    start = datetime.date(2026, 3, 5)  # Day 1
    today = datetime.date.today()
    return max(1, (today - start).days + 1)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="MiganCore Tracker CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Show system state (git + API)")

    # day-start
    p_ds = sub.add_parser("day-start", help="Generate pre-execution brief")
    p_ds.add_argument("day", type=int, help="Day number")
    p_ds.add_argument("--topic", "-t", default="general", help="Topic slug")

    # day-end
    p_de = sub.add_parser("day-end", help="Generate end-of-day wrap")
    p_de.add_argument("day", type=int, help="Day number")

    # agent-sync
    p_as = sub.add_parser("agent-sync", help="Generate Claude plan file for agents")
    p_as.add_argument("topic", help="Topic (e.g. 'Hafidz Ledger Phase A')")
    p_as.add_argument("--day", "-d", type=int, help="Day number (default: inferred)")

    # agent-read
    p_ar = sub.add_parser("agent-read", help="Read agent review file")
    p_ar.add_argument("agent", choices=["kimi", "codex"], help="Agent name")
    p_ar.add_argument("--day", "-d", type=int, help="Day number")
    p_ar.add_argument("--topic", "-t", default="general", help="Topic")

    # agent-recap
    p_rc = sub.add_parser("agent-recap", help="Generate recap from all reviews")
    p_rc.add_argument("--day", "-d", type=int, help="Day number")
    p_rc.add_argument("--topic", "-t", default="general", help="Topic")

    # backlog
    sub.add_parser("backlog", help="Show prioritized backlog")

    # lesson
    p_ls = sub.add_parser("lesson", help="Append lesson to tracker")
    p_ls.add_argument("text", help="Lesson text")
    p_ls.add_argument("--day", "-d", type=int, help="Day number")

    # align
    sub.add_parser("align", help="Show vision alignment map")

    # update
    sub.add_parser("update", help="Update QUICK_STATUS from live state")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\nQuick start:")
        print("  python scripts/tracker.py status")
        print("  python scripts/tracker.py day-start 69 --topic 'Cycle 6 Eval'")
        print("  python scripts/tracker.py agent-sync 'Hafidz Ledger Phase A'")
        sys.exit(0)

    commands = {
        "status": cmd_status,
        "day-start": cmd_day_start,
        "day-end": cmd_day_end,
        "agent-sync": cmd_agent_sync,
        "agent-read": cmd_agent_read,
        "agent-recap": cmd_agent_recap,
        "backlog": cmd_backlog,
        "lesson": cmd_lesson,
        "align": cmd_align,
        "update": cmd_update,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
