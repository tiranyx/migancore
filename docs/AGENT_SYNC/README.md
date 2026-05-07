# AGENT SYNC — Multi-Agent Coordination Files

This directory is the **file-based message bus** for Claude, Kimi, and Codex coordination.

## Protocol

```
Claude → CLAUDE_PLAN_{day}_{TOPIC}.md     (execution plan + research questions)
Kimi   → KIMI_REVIEW_{day}_{TOPIC}.md    (analysis + go/no-go + research findings)
Codex  → CODEX_QA_{day}_{TOPIC}.md       (security findings + logic bugs + sign-off)
Claude → RECAP_{day}_{TOPIC}.md          (final decisions + lessons + next steps)
EOD    → DAY_{day}_EOD_WRAP.md           (end-of-day wrap)
```

## How to Use

### Claude (implementator)
```bash
# Start a coordination cycle:
python scripts/tracker.py agent-sync "Topic Name" --day 69

# Read Kimi's response:
python scripts/tracker.py agent-read kimi --day 69 --topic "Topic Name"

# Write final recap:
python scripts/tracker.py agent-recap --day 69 --topic "Topic Name"
```

### Kimi (researcher + reviewer, VS Code)
1. Open `CLAUDE_PLAN_{day}_{TOPIC}.md` in VS Code
2. Read Claude's plan, execute research on the questions
3. Write response to `KIMI_REVIEW_{day}_{TOPIC}.md` using this template:

```markdown
# KIMI REVIEW — Day N: Topic

## VERDICT: GO / NO-GO / CONDITIONAL

## RESEARCH FINDINGS
[Answer Claude's research questions with sources]

## ANALYSIS
[Kimi's independent analysis of the plan]

## RISKS MISSED BY CLAUDE
[Anything Claude didn't consider]

## RECOMMENDATION
[If CONDITIONAL: specific changes before Claude proceeds]
```

### Codex (QA + security)
1. Read `CLAUDE_PLAN_*` + `KIMI_REVIEW_*`
2. Write to `CODEX_QA_{day}_{TOPIC}.md`:

```markdown
# CODEX QA — Day N: Topic

## SECURITY FINDINGS
(Severity: P1/P2/P3, file:line, description)

## LOGIC BUGS
[Any obvious flaws in execution plan or proposed code]

## MISSING TESTS
[What should be tested before shipping]

## SIGN-OFF: YES / CONDITIONAL / NO
[If CONDITIONAL: what must be fixed]
```

## File Naming

- Day number: `69`, `70`, etc.
- Topic slug: uppercase, underscores, max 30 chars. e.g. `HAFIDZ_LEDGER_PHASE_A`
- Full example: `CLAUDE_PLAN_69_HAFIDZ_LEDGER_PHASE_A.md`

## Rules

1. **Files are committed** — this is the audit trail, not a temp workspace.
2. **Claude always reads both Kimi + Codex** before writing RECAP.
3. **Kimi does NOT execute** — research only, no code changes.
4. **Codex does NOT implement fixes** — finding only, Claude implements.
5. **One coordination cycle per topic per day** — don't stack topics.
