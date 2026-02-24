---
id: AIPIP-0008
title: Fix session-resume.sh Pipefail Bug
status: accepted
created: 2026-02-24
created-by: claude
---

# AIPIP-0008: Fix session-resume.sh Pipefail Bug

## Problem

The `session-resume.sh` hook (wired to `SessionStart`) fails with exit code 1 whenever there is **no active feature**. This is the default state — most sessions start without a feature in progress.

**Root cause:** Line 14 uses a pipeline with `set -euo pipefail`:

```bash
PHASE_FILE=$(find "$PROJECT_DIR/.specs/active" -name "PHASE" 2>/dev/null | grep -v '.gitkeep' | head -1)
```

When no `PHASE` file exists (only `.gitkeep`), the pipeline behaves as follows:
1. `find` outputs `.gitkeep` — exit 0
2. `grep -v '.gitkeep'` filters it out, producing no output — **exit 1** (grep returns 1 when no lines match)
3. `head -1` gets empty input — exit 0

With `pipefail`, the pipeline's exit code is 1 (from grep). With `set -e`, this kills the script immediately — before it reaches the empty-check on line 16 that would have handled this case gracefully with `exit 0`.

**Impact:** Every session start without an active feature triggers a hook error. The hook is non-blocking (SessionStart hooks don't block), so it's cosmetic, but it produces spurious error output and masks the hook's intended behavior.

## Proposal

Append `|| true` to the find pipeline on line 14 of `.claude/hooks/session-resume.sh`:

```bash
# Before (broken)
PHASE_FILE=$(find "$PROJECT_DIR/.specs/active" -name "PHASE" 2>/dev/null | grep -v '.gitkeep' | head -1)

# After (fixed)
PHASE_FILE=$(find "$PROJECT_DIR/.specs/active" -name "PHASE" 2>/dev/null | grep -v '.gitkeep' | head -1 || true)
```

This allows the empty-string check on line 16 to handle the "no active feature" case as originally intended.

No other changes needed. The rest of the script is correct.

## Alternatives Considered

### A. Remove `set -euo pipefail`
Would fix the bug but weakens error handling for the rest of the script. Other commands in the script (git, cat) should still fail fast on unexpected errors.

### B. Use `find -not -name '.gitkeep'` instead of piping to grep
Would avoid the grep exit code issue, but is less readable and doesn't match the existing pattern. Also, `find` with `-not -name` still returns exit 0 with no results, so it works — but `|| true` is the more minimal and conventional fix.

### C. Replace the pipeline with a for-loop over find results
Over-engineered for a one-line fix.

## Impact

### Modified files

| File | Change |
|------|--------|
| `.claude/hooks/session-resume.sh` | Add `\|\| true` to line 14 pipeline |
| `.claude/hooks/branch-protection.sh` | Add `\|\| true` to line 47 pipeline |
| `.claude/hooks/pre-commit-checks.sh` | Add `\|\| true` to lines 49 and 57 pipelines |

### Process changes

None. This is a bugfix to an existing hook — no behavioral change. The hook already intended to exit 0 when no active feature exists; this fix makes it actually do so.

## Change Log

| Date | Change |
|------|--------|
| 2026-02-24 | Initial proposal — bugfix for pipefail + grep interaction |
| 2026-02-24 | Accepted and implemented. Added `\|\| true` to session-resume.sh line 14. Verified exit code 0. |
| 2026-02-24 | Extended to branch-protection.sh (line 47) and pre-commit-checks.sh (lines 49, 57) — same bug. |
