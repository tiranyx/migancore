# AGENT SYNC — Multi-Agent Coordination Protocol
<!-- Single source of truth for Claude, Kimi, Codex coordination. -->
<!-- Update this file when roles, rituals, or file formats change. -->

This directory is the **file-based message bus** and **shared documentation hub**
for the MiganCore multi-agent team. No real-time protocol needed — drop a file,
the watcher pings the next agent.

---

## 1. ROLE & DOCUMENTATION RESPONSIBILITIES

Each agent owns specific documentation. If you produced it, you write it.
"Produced" = executed, researched, or reviewed it.

| Agent | Role | Owns (must write) |
|-------|------|--------------------|
| **Claude** | Implementor + Orchestrator | `CLAUDE_PLAN_*.md` · `RECAP_*.md` · `MIGANCORE_TRACKER.md` · Lesson entries · Day log entries |
| **Kimi** | Researcher + Reviewer | `KIMI_REVIEW_*.md` · Research summaries · Lesson entries for findings Kimi surfaces |
| **Codex** | QA + Security | `CODEX_QA_*.md` · Bug/security reports · Lesson entries for bugs Codex finds |
| **Fahmi** | Founder + Decision-Maker | Final GO/NO-GO decisions · Priority changes (via chat to Claude) |

### Non-negotiable documentation rules:

1. **Every Cycle eval → KIMI_REVIEW + CODEX_QA mandatory.** Not optional. Cycle eval = write your file.
2. **Every deploy → Claude writes RECAP + updates Day log.** Same session, same day.
3. **Every lesson must be committed.** `python scripts/tracker.py lesson "TEXT"` or manual edit.
4. **No orphan findings.** If you find a bug or insight, it goes in a file — not just in chat.

---

## 2. FILE PROTOCOL

```
Claude  → CLAUDE_PLAN_{day}_{TOPIC}.md      execution plan + research questions for Kimi
Kimi    → KIMI_REVIEW_{day}_{TOPIC}.md      analysis + GO/NO-GO + lessons Kimi found
Codex   → CODEX_QA_{day}_{TOPIC}.md         security/logic findings + sign-off
Claude  → RECAP_{day}_{TOPIC}.md            final decisions + lessons + next steps
Claude  → DAY_{day}_EOD_WRAP.md             end-of-day wrap (only if no RECAP exists)
```

All files are committed — this is the audit trail.

---

## 3. DAILY RITUAL (WHEN TO WRITE)

```
SESSION START   → Claude: read latest KIMI_REVIEW + CODEX_QA, update tracker status
                  Kimi: pick up latest CLAUDE_PLAN, start research
                  Codex: pick up latest CLAUDE_PLAN + KIMI_REVIEW, start QA

DURING SESSION  → each agent drops their file when done (watcher pings next agent)

SESSION END     → Claude: write RECAP + run `tracker.py day-end N`
                  All: make sure your file is committed before closing

CYCLE EVAL      → always triggers: CLAUDE_PLAN (eval plan) → KIMI_REVIEW (analysis)
                  → CODEX_QA (gate verification) → RECAP (decision)
```

---

## 4. FILE TEMPLATES

### CLAUDE_PLAN_{day}_{TOPIC}.md
```markdown
# CLAUDE PLAN — Day N: Topic

## OBJECTIVE
[What we're building / fixing / deciding]

## CONTEXT
[Relevant state: metrics, errors, prior decisions]

## EXECUTION PLAN
[Step-by-step what Claude will do]

## RESEARCH QUESTIONS FOR KIMI
1. [Question]
2. [Question]

## QA QUESTIONS FOR CODEX
1. [What to verify / attack]

## RISKS CLAUDE SEES
[Known risks, open questions]

## SUCCESS CRITERIA
[How we know it worked]
```

### KIMI_REVIEW_{day}_{TOPIC}.md
```markdown
# KIMI REVIEW — Day N: Topic

## VERDICT: GO / NO-GO / CONDITIONAL

## RESEARCH FINDINGS
[Answer Claude's research questions with sources]

## ANALYSIS
[Kimi's independent read of the plan — agree / disagree / gaps]

## RISKS MISSED BY CLAUDE
[Anything Claude didn't consider]

## LESSONS KIMI SURFACED
- #N (proposed): [lesson text]

## RECOMMENDATION
[If CONDITIONAL: specific changes required before Claude proceeds]
```

### CODEX_QA_{day}_{TOPIC}.md
```markdown
# CODEX QA — Day N: Topic

## SIGN-OFF: YES / CONDITIONAL / NO

## SECURITY FINDINGS
| Severity | File:Line | Description | Fix |
|----------|-----------|-------------|-----|
| P1       | ...       | ...         | ... |

## LOGIC BUGS
[Flaws in execution plan or proposed code]

## MISSING TESTS
[What must be verified before shipping]

## LESSONS CODEX SURFACED
- #N (proposed): [lesson text]

## RECURRING PATTERNS (reference)
- P0: race conditions on async DB writes (Lesson #156)
- P0: UI state not rolled back on API error (Lesson #157)
- P1: eval script threshold mismatch (Lesson #155, #144, #140)
- P1: secrets in committed docs (Lesson #151)
- P2: retry logic too narrow (only HTTP 500, not timeout/connect)
```

### RECAP_{day}_{TOPIC}.md
```markdown
# RECAP — Day N: Topic

## DECISION
[GO / ROLLBACK / DEFER + reason]

## WHAT WAS DONE
[Bullet list of completed actions]

## WHAT CHANGED IN PRODUCTION
[Files deployed, containers rebuilt, configs changed]

## LESSONS LOCKED
[#N: text — each lesson from this cycle]

## NEXT STEPS
[P0 items for next session]
```

---

## 5. LESSON WORKFLOW

Any agent can propose a lesson. Claude locks it into the tracker.

```
Kimi finds something → writes "#N (proposed): text" in KIMI_REVIEW
Codex finds something → writes "#N (proposed): text" in CODEX_QA
Claude reviews RECAP → assigns real number → `tracker.py lesson "TEXT"`
→ committed to MIGANCORE_TRACKER.md lesson registry
```

Lesson numbers are sequential across all agents. Claude assigns final numbers.

---

## 6. TRACKER OWNERSHIP

`docs/MIGANCORE_TRACKER.md` is Claude's responsibility to maintain.
Kimi and Codex contribute via their review files — Claude pulls findings into the tracker.

| Section | Updated by | When |
|---------|-----------|------|
| Quick Status | Claude | Every session start/end |
| Vision Alignment Map | Claude | After major milestone |
| Active Roadmap | Claude | After GO/ROLLBACK decisions |
| Backlog | Claude | When items added/closed |
| Daily Log | Claude | Session end (day-end ritual) |
| Lesson Registry | Claude (with input from Kimi + Codex) | After each recap |
| Training Metrics | Claude | After each cycle eval |
| Research Agenda | All agents | Anyone can add open questions |

---

## 7. FILE NAMING

- Day number: `69`, `70`, etc.
- Topic slug: UPPERCASE, underscores, max 30 chars
- Examples:
  - `CLAUDE_PLAN_70_CYCLE7_DATASET.md`
  - `KIMI_REVIEW_70_CYCLE7_DATASET.md`
  - `CODEX_QA_70_CYCLE7_DATASET.md`
  - `RECAP_70_CYCLE7_DATASET.md`

---

## 8. HARD RULES

1. **Files are committed** — this is the audit trail, not temp workspace.
2. **Claude reads both Kimi + Codex before writing RECAP.** No shortcuts.
3. **Kimi does NOT execute code** — research and review only.
4. **Codex does NOT implement fixes** — findings only, Claude implements.
5. **Fahmi's decisions override all.** GO/NO-GO from Fahmi = final.
6. **One coordination cycle per topic per day.** No stacking.
7. **Lessons must be committed the same day they are found.** No backlog of unrecorded lessons.
