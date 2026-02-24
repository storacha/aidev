---
id: AIPIP-0006
title: Context Isolation and Task Ordering Enforcement
status: accepted
created: 2026-02-20
created-by: alex
last-updated: 2026-02-20
updated-by: claude
---

# AIPIP-0006: Context Isolation and Task Ordering Enforcement

## Problem

The process retro after `guppy-gateway-cli-ux` identified 4 unenforced areas. AIPIP-0005 addressed session continuity and review gating, but three gaps remain:

### Gap 1: Subagent isolation for test writing is unenforced

Phase 3 acceptance tests are supposed to be written by a subagent (Task tool) to prevent implementation knowledge from leaking into test design. This is documented in the `/plan` skill but has **zero enforcement** — nothing stops the implementing agent from writing tests directly in its own context. The guppy feature's tests were written by the main agent, violating context isolation.

Research (AIPIP-0001, `research/tdd-ai-agents.md`) shows that when the same agent writes both design notes and tests, test quality degrades because the agent unconsciously designs tests around the implementation it has in mind rather than the spec.

### Gap 2: Code review is not required to use a subagent

The final code review (`/review --final`) is supposed to be an independent verification, but nothing enforces that it's performed by a separate subagent. The implementing agent could run the review in its own context, defeating the purpose of independent verification — the same bias problem as Gap 1 but at review time.

### Gap 3: Task ordering during Phase 4 is unenforced

Tasks have explicit dependency notation (`Task 3 (after: 1, 2)`), but nothing tracks which task is currently being worked on or verifies that prerequisites are complete. If a session is interrupted mid-task and resumed, the agent doesn't know which task it was on. The process also can't detect if the agent skips ahead to a dependent task.

## Proposal

### Fix 1: Subagent Attestation Gate

Add a `subagent-attestation.json` artifact written after Phase 3 test-writing. The `review-gate.sh` hook blocks the decompose→implement transition unless this file exists.

**Attestation file format:**
```json
{
  "written_by": "subagent",
  "timestamp": "ISO8601",
  "test_files": ["list of test file paths produced"],
  "brief_hash": "first 8 chars of sha256 of brief.md content"
}
```

**Enforcement:** `review-gate.sh` checks for `$SPEC_DIR/subagent-attestation.json` when the PHASE is being set to `implement`. Missing file → exit 2 (blocked).

**Skill update:** The `/plan` skill (SKILL.md) step 4d writes this attestation after the subagent produces tests and they're copied to `tests-snapshot/`.

### Fix 2: Mandatory Subagent for Code Review

Update the `/plan` skill, `/review` skill, and rule files to explicitly require that the final code review is performed by a subagent (Task tool with fresh context). The implementing agent must NOT review its own code in the same conversation context.

**Enforcement level:** Rules + skill instructions (Tier 1). A hook-based enforcement would require detecting whether the current agent is the same as the reviewer, which isn't feasible with shell hooks. The `/review` skill already uses `subagent_type: "general-purpose"` — this fix makes the requirement explicit and non-optional.

**Files updated:**
- `/plan` skill: "After ALL Tasks Complete" section requires subagent
- `review-process.md`: "Context Isolation (Mandatory)" section
- `development-workflow.md`: Subagent requirement in "Mandatory Code Review" section

### Fix 3: CURRENT_TASK State Tracking

Add a `CURRENT_TASK` file to the spec directory that tracks which task is being worked on during Phase 4. This serves two purposes:

1. **Session continuity:** The `session-resume.sh` hook injects the current task number on session boundaries, so interrupted work can be resumed correctly.
2. **Dependency awareness:** Before starting a task, the agent reads `tasks.md` to verify all predecessor tasks are marked ✓. The explicit tracking makes this verifiable.

**File:** `.specs/active/{feature-slug}/CURRENT_TASK` — contains the task number (e.g., `2`).

**Lifecycle:**
- Written before starting each task in Phase 4
- Updated to the next task number after completing a task
- Deleted (or left at final task) when all tasks are done

**Enforcement level:** Skill instructions + session-resume hook (Tier 1-2). The skill (step 2 in the per-task loop) writes the file; the session-resume hook reads it. A full hook-based enforcement of dependency ordering would require parsing the task dependency graph in shell, which is fragile. The task completion check in `review-gate.sh` (all tasks must be ✓ before implement→complete) provides the backstop.

## Alternatives Considered

### A. Hook-based dependency enforcement
Write a shell hook that parses `tasks.md`, extracts the dependency graph, reads `CURRENT_TASK`, and blocks writes if prerequisites aren't met. **Rejected** — parsing markdown task dependency notation in bash is fragile and error-prone. The backstop (all tasks ✓ before completion) catches the failure mode that matters.

### B. Database/ledger for task state
Use a structured JSON file instead of CURRENT_TASK plain text. **Rejected as over-engineering** — a single number in a file is sufficient. The `tasks.md` file is the source of truth for completion status; CURRENT_TASK is a lightweight pointer.

### C. Agent-based hook for subagent attestation verification
Instead of checking for a file, use an agent hook that verifies the tests were actually produced by a subagent by inspecting the conversation history. **Rejected** — agent hooks are slow, and conversation history isn't accessible to hooks. The attestation file is a pragmatic proxy.

## Impact

### Modified files

| File | Change |
|------|--------|
| `.claude/hooks/review-gate.sh` | Add decompose→implement gate checking `subagent-attestation.json` + `tests-snapshot/` |
| `.claude/hooks/session-resume.sh` | Inject `CURRENT_TASK` state on session resume |
| `.claude/skills/plan/SKILL.md` | Step 4d (attestation), step 2 in per-task loop (CURRENT_TASK), subagent requirement for review, renumber steps, update reference tables |
| `.claude/rules/review-process.md` | Add "Context Isolation (Mandatory)" with subagent requirement |
| `.claude/rules/development-workflow.md` | Add subagent requirement to "Mandatory Code Review" section |

### New artifacts (per feature)

| File | Phase | Purpose |
|------|-------|---------|
| `subagent-attestation.json` | Decompose (Phase 3) | Proves tests were written by isolated subagent |
| `CURRENT_TASK` | Implement (Phase 4) | Tracks which task is in progress |

### Process changes

- Decompose→implement transition now requires **two** artifacts: `tests-snapshot/` AND `subagent-attestation.json`
- Code review is explicitly a subagent operation (was implicit before)
- Per-task state is tracked for session continuity

### What does NOT change

- The workflow phases themselves
- The review-gate.sh implement→complete checks (already in place)
- The test freeze rule
- Human review gates

## Change Log

| Date | Change |
|------|--------|
| 2026-02-20 | Initial proposal based on process retro gaps #3 and #4 |
| 2026-02-20 | Accepted. Changes already implemented in skill/hook/rule files. |
