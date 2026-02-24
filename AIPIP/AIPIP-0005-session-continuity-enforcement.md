---
id: AIPIP-0005
title: Session Continuity and Process Enforcement Hooks
status: accepted
created: 2026-02-20
created-by: alex
last-updated: 2026-02-20
updated-by: claude
---

# AIPIP-0005: Session Continuity and Process Enforcement Hooks

## Problem

During the `guppy-gateway-cli-ux` feature implementation, the process failed silently:

1. **No feature branch** — all code was written to `main`'s working tree
2. **Tasks not marked complete** — `tasks.md` still shows `[ ]` for all 3 tasks despite implementation being done
3. **No review agent called** — `/review --phase4` was never run after any task
4. **No telemetry logged** — `.specs/telemetry.jsonl` doesn't exist
5. **PHASE file stale** — says `implement` but implementation is complete

The root cause: every process step is enforced only by **rules files** (CLAUDE.md, `.claude/rules/*.md`). Rules are Tier 1 enforcement (~60-80% compliance). When a session ends mid-task or context gets long, the model forgets or skips process steps. There are **zero hooks** (Tier 2, ~90%+ compliance) enforcing any invariant.

This is the exact failure mode AIPIP-0001 predicted under "3-layer enforcement" — we built the rules layer but never built the hooks layer.

## Proposal

Add **5 hooks** that enforce the most critical process invariants. These are deterministic shell scripts that read filesystem state and block actions when prerequisites aren't met.

### Hook 1: Session Resume (`SessionStart`)

**Triggers on:** `startup`, `resume`, `compact`

**Purpose:** Re-inject active feature state into context at every session boundary. This is the #1 fix — without it, a new/resumed session has no idea what phase it's in, what tasks are done, or what branch it should be on.

**Behavior:**
- Read `.specs/active/*/PHASE` to find the active feature and phase
- Read `.specs/active/*/tasks.md` to show task completion status
- Show current git branch and uncommitted changes
- If on `main` with an active feature in `implement` phase, warn to create a feature branch
- Output is injected into the agent's context as a system message

### Hook 2: Branch Protection (`PreToolUse` → `Bash`)

**Triggers on:** Any `Bash` tool call containing `git commit` or `git push`

**Purpose:** Prevent committing or pushing directly to `main`/`master` when a feature is active.

**Behavior:**
- Parse the bash command for `git commit` or `git push`
- Check current branch via `git branch --show-current`
- If on `main`/`master`, **exit 2** (block) with message suggesting `git checkout -b feat/<feature>`
- Allow all other git operations (status, diff, log, branch, checkout)

### Hook 3: Phase Gate (`PreToolUse` → `Edit|Write`)

**Triggers on:** Any `Edit` or `Write` tool call targeting a source file

**Purpose:** Enforce phase constraints — no source files in specify/design, no non-test files in decompose.

**Behavior:**
- Read the PHASE file from `.specs/active/*/PHASE`
- In `specify` or `design` phase: block writes to `.go`, `.ts`, `.js`, `.py` files (except under `.specs/` or `.claude/`)
- In `decompose` phase: block writes to source files that aren't test files (`*_test.go`, `*.test.ts`, `*.spec.js`)
- In `implement` or later: allow all writes
- No active feature: allow all writes (Tier 0 work)

### Hook 4: Task Completion Gate (`PreToolUse` → `Bash`)

**Triggers on:** Any `Bash` command containing `git commit` (the final step before Phase 5)

**Purpose:** Before any commit, verify that the process was followed — we're on a feature branch, tests pass, and tasks are tracked.

**Behavior:**
- Check current branch is not `main`/`master` (overlaps with Hook 2, defense in depth)
- Check that a PHASE file exists and is in `implement` or `complete`
- Run the test suite for the affected package (parse staged files to determine package)
- If any check fails, **exit 2** with specific remediation instructions

*Note: This is separate from Hook 2 because it adds test verification and phase checks beyond just branch protection.*

### Hook 5: Stop Guard (`Stop`)

**Triggers on:** Every time the agent is about to stop responding

**Purpose:** Catch the "session ends mid-process" failure. If there's an active feature with in-progress work, warn the agent to update process state before stopping.

**Behavior (agent-based hook):**
- Check if `.specs/active/*/PHASE` exists with phase `implement`
- Check for uncommitted changes (`git status --porcelain`)
- Check if any tasks in `tasks.md` should be marked complete based on test results
- If issues found, respond with `{"ok": false, "reason": "..."}` to nudge the agent to update state
- Include a `stop_hook_active` guard to prevent infinite recursion

## Alternatives Considered

### A. Agent-based hooks for everything
Using `type: "agent"` hooks instead of `type: "command"` for all hooks. **Rejected** — agent hooks are slow (10-30s each), consume tokens, and are overkill for deterministic checks. Reserve agent hooks for judgment calls (Hook 5 only).

### B. Git pre-commit hooks (`.git/hooks/pre-commit`)
Standard git hooks that prevent commits to main. **Partially adopted** — these work but only catch commits, not the broader process failures (missing reviews, unmarked tasks). They also don't help with session continuity. Used as Tier 3 (defense in depth) but not the primary mechanism.

### C. GitHub branch protection rules
Server-side rules preventing pushes to main. **Complementary, not sufficient** — these only fire on push, not on local commits. They don't help with any of the session-continuity or process-tracking failures. Should be enabled on the remote repo but aren't a substitute for local enforcement.

### D. Persistent task list via `CLAUDE_CODE_TASK_LIST_ID`
Using Claude Code's native Tasks API with a persistent task list ID. **Adopted as supplementary** — this helps tasks survive session boundaries but doesn't enforce that tasks ARE tracked in the first place. The hooks above enforce; the persistent task list provides the storage.

### E. Full continuity system (Continuous-Claude-v3 pattern)
30+ hooks, ledger files, PostgreSQL-backed file claims. **Rejected** — massive complexity, fragile, and the overhead would violate the "shouldn't feel like a burden" principle. Our 5-hook approach covers the critical paths.

## Impact

### New files

| File | Purpose |
|------|---------|
| `.claude/hooks/session-resume.sh` | Hook 1: Session state injection |
| `.claude/hooks/branch-protection.sh` | Hook 2: Block commits to main |
| `.claude/hooks/phase-gate.sh` | Hook 3: Phase-aware write blocking |
| `.claude/hooks/pre-commit-checks.sh` | Hook 4: Pre-commit verification |
| `.claude/hooks/stop-guard-prompt.md` | Hook 5: Stop guard agent prompt |
| `.claude/settings.json` | Hook wiring configuration |

### Modified files

| File | Change |
|------|--------|
| `CLAUDE.md` | Add "Enforcement Hooks" section documenting the hooks |
| `memory/MEMORY.md` | Update with AIPIP-0005 entry |
| `.claude/rules/development-workflow.md` | Reference hooks as enforcement mechanism |

### Process changes

- **Session resume** becomes automatic — no manual state-checking needed
- **Feature branch creation** becomes mandatory during implement phase (agent is prompted to create one)
- **Phase constraints** are enforced, not just documented
- **Commits** require tests passing and correct branch

### What does NOT change

- The workflow phases themselves (specify → design → decompose → implement → complete)
- The rules files (they remain as Tier 1 guidance; hooks are Tier 2 enforcement)
- The review process (still invoked by the agent, not enforced by hooks — see Future Work)
- The human review gates (still use AskUserQuestion)

## Implementation Plan

### Phase A: Core hooks (Hooks 1-3)
1. Create `.claude/hooks/` directory
2. Write `session-resume.sh` — reads PHASE, tasks.md, git state
3. Write `branch-protection.sh` — blocks git commit/push on main
4. Write `phase-gate.sh` — blocks source writes in wrong phase
5. Create `.claude/settings.json` wiring all three hooks
6. Test each hook manually

### Phase B: Commit and stop guards (Hooks 4-5)
7. Write `pre-commit-checks.sh` — verifies tests + branch + phase before commit
8. Write `stop-guard-prompt.md` — agent prompt for Stop hook
9. Wire hooks 4-5 into settings.json
10. Test stop guard for infinite-loop safety

### Phase C: Integration and docs
11. Update CLAUDE.md with enforcement hooks section
12. Update development-workflow.md to reference hooks
13. Update MEMORY.md with AIPIP-0005 entry
14. Dry-run: reset the guppy feature to decompose phase and re-implement with hooks active

## Future Work

- ~~**Review enforcement hook**~~: Implemented as `review-gate.sh`. The `/review` skill now writes JSON artifacts to `.specs/active/{feature}/reviews/`. The hook blocks PHASE transitions (decompose→implement, implement→complete) unless required review artifacts exist.
- **Persistent task list**: Set `CLAUDE_CODE_TASK_LIST_ID` per-project so tasks survive across sessions automatically. Requires testing the Tasks API cross-session behavior.
- **Telemetry hook**: Auto-append to `.specs/telemetry.jsonl` on phase transitions, hook blocks, and task completions. Currently manual and easily forgotten.
- **Pre-compact hook**: Save critical state before context compaction (the most common "invisible session boundary").

## Change Log

| Date | Change |
|------|--------|
| 2026-02-20 | Initial proposal based on guppy-gateway-cli-ux process failure |
| 2026-02-20 | Implemented: 3 new hooks + wired all 8 hooks via settings.json. Existing hooks discovered and preserved. |
| 2026-02-20 | Added review-gate.sh hook + updated /review skill to write JSON artifacts. 9 hooks total. Review enforcement moved from Future Work to done. |
