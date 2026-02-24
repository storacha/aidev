---
id: AIPIP-0007
title: Require AIPIP Before Any Process Change
status: accepted
created: 2026-02-20
created-by: alex
last-updated: 2026-02-20
updated-by: claude
---

# AIPIP-0007: Require AIPIP Before Any Process Change

## Problem

Process files (rules, skills, hooks, settings) were modified without a formal AIPIP being written and accepted first. This happened during AIPIP-0006 implementation — the changes were made directly to process files before the AIPIP documenting them existed.

AIPIP-0004 established the governance model (all process changes need AIPIPs), but there is no enforcement mechanism preventing the AI from modifying process files when asked to "just do it." The AI needs a hard rule: refuse to modify process files without an accepted AIPIP, and tell the user to create one first.

## Proposal

### 1. Process File Protection Rule

Add a rule to `.claude/rules/process-governance.md` (new file) that defines:

**Protected files** (process files that require an AIPIP):
- `.claude/rules/*.md` — workflow rules
- `.claude/skills/*/SKILL.md` — skill definitions
- `.claude/hooks/*.sh` — enforcement hook scripts
- `.claude/hooks/*.md` — hook agent prompts
- `.claude/settings.json` — hook wiring configuration

**Rule:** Before modifying any protected file, you MUST:
1. Check that a relevant AIPIP exists in `plans/` with status `accepted`
2. If no AIPIP exists, tell the user: "This requires a process change. Please create an AIPIP first (see `plans/README.md` for the format), or ask me to draft one."
3. Do NOT modify the file until the AIPIP is accepted by the user

**Exception:** Creating a new AIPIP document (`plans/AIPIP-*.md`) and updating `plans/README.md` registry are always allowed — these are the proposal mechanism itself.

### 2. Process Change Guard Hook

Add a PreToolUse hook (`process-guard.sh`) that fires on Write/Edit and:
- Checks if the target file matches a protected path pattern
- Reads the AIPIP registry to see if there's an `accepted` AIPIP referencing this file
- If no accepted AIPIP covers the change, blocks with exit 2 and a message explaining the requirement

**Hook logic:**
```
1. Is the target file a protected process file? If not, exit 0 (allow).
2. Is there an accepted AIPIP that lists this file in its Impact section?
   - Scan plans/AIPIP-*.md for status: accepted and the file path in Impact.
   - If found, exit 0 (allow).
3. Block with message: "BLOCKED: Modifying process file requires an accepted AIPIP."
```

**Implementation:** Token-based gating. The hook checks for `.claude/.process-change-token`. The agent writes this token (containing the AIPIP ID) after the user accepts the AIPIP, implements changes, then deletes the token. This avoids fragile YAML/filename parsing while providing a clear, unambiguous gate.

### 3. Agent Behavior Rule

The agent MUST follow this decision tree when asked to change process behavior:

```
User asks for process change
  → "This is a process change. I need to write an AIPIP first."
  → Draft AIPIP-NNNN as `proposed`
  → Present to user for review
  → User accepts → Update AIPIP status to `accepted`
  → THEN implement the changes
  → Update AIPIP change log
```

The agent must NEVER:
- Modify process files "while implementing" without prior AIPIP
- Combine feature implementation with process changes in the same action
- Skip the AIPIP because "it's a small change" — all process changes need traceability

## Alternatives Considered

### A. Rule-only enforcement
Just add the governance rule without a hook. **Insufficient** — this is exactly the approach that failed (AIPIP-0004 established the rule, but the AI ignored it under task pressure). Rules are Tier 1 (~60-80% compliance).

### B. Strict AIPIP-file-matching hook
Parse each AIPIP's YAML and Impact section to verify coverage. **Rejected as fragile** — bash YAML parsing is unreliable. The simpler approach (block all process file writes, let the rule handle AIPIP verification) is more robust.

### C. Git-based protection
Use `.gitattributes` or pre-commit hooks to prevent process file changes without a tag/label. **Complementary but insufficient** — these only fire on commit, not on edit. The PreToolUse hook catches the change earlier.

## Impact

### New files

| File | Purpose |
|------|---------|
| `.claude/rules/process-governance.md` | Rule defining protected files and AIPIP requirement |
| `.claude/hooks/process-guard.sh` | Hook blocking writes to process files |

### Modified files

| File | Change |
|------|--------|
| `.claude/settings.json` | Wire `process-guard.sh` into PreToolUse Write/Edit matcher |
| `plans/README.md` | Add AIPIP-0007 to registry |
| `memory/MEMORY.md` | Add AIPIP-0007 entry |

### Process changes

- All process file modifications require an accepted AIPIP first
- Agent must refuse and redirect to AIPIP creation when asked to change process files directly
- New hook provides Tier 2 enforcement of this rule

## Change Log

| Date | Change |
|------|--------|
| 2026-02-20 | Initial proposal based on AIPIP-0006 governance violation |
| 2026-02-20 | Accepted. Implemented with token-based gating (.claude/.process-change-token). Hook tested: blocks without token, allows with token, passes non-process files. |
