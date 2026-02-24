---
id: AIPIP-0010
title: Fix sed regex macOS compatibility in hooks
status: accepted
created: 2026-02-24
created-by: claude
---

# AIPIP-0010: Fix sed regex macOS compatibility in hooks

## Problem

`branch-protection.sh` and `pre-commit-checks.sh` use `\s` (Perl-style shorthand for whitespace) in `sed -nE` regex patterns to extract repo paths from `cd` and `git -C` commands. macOS `sed` does not support `\s` — it silently fails to match, returning no output.

This means **path extraction never works on macOS**, so the hooks cannot determine which repo a git command targets. They fall through to the project directory (which isn't a git repo in this workspace), get an empty branch name, and allow the commit unconditionally.

**Affected lines:**
- `branch-protection.sh` lines 27, 31 — `cd` and `git -C` path extraction
- `pre-commit-checks.sh` lines 33, 36 — identical patterns

**Not affected:** `grep -qE` with `\s` works fine on macOS (grep supports it). Only the `sed` calls are broken.

## Proposal

Replace `\s` with `[[:space:]]` (POSIX character class) in all four sed patterns. POSIX classes work on both macOS and Linux sed.

```bash
# Before (broken on macOS)
sed -nE 's/^\s*cd\s+"?([^"&;]+)"?\s*(&&|;).*/\1/p'
sed -nE 's/.*git\s+-C\s+"?([^"]+)"?\s+.*/\1/p'

# After (works everywhere)
sed -nE 's/^[[:space:]]*cd[[:space:]]+"?([^"&;]+)"?[[:space:]]*(&&|;).*/\1/p'
sed -nE 's/.*git[[:space:]]+-C[[:space:]]+"?([^"]+)"?[[:space:]]+.*/\1/p'
```

## Alternatives Considered

### A. Use GNU sed via Homebrew
Requires `gsed` to be installed. Adds an external dependency for a simple regex fix.

### B. Use Perl instead of sed
Works but over-engineered — `[[:space:]]` is the standard POSIX fix.

### C. Use `tr` or `awk` instead
More verbose, less readable. `sed` with POSIX classes is the right tool.

## Impact

### Modified files

| File | Change |
|------|--------|
| `.claude/hooks/branch-protection.sh` | (1) `\s` → `[[:space:]]` in sed, (2) trim trailing space in cd regex, (3) split git -C regex into quoted/unquoted, (4) relax initial detection to `git\s+.*\b(commit\|push)\b` |
| `.claude/hooks/pre-commit-checks.sh` | Same 4 fixes |

### Process changes

None. Bugfix only — makes existing path extraction and command detection work on macOS.

## Change Log

| Date | Change |
|------|--------|
| 2026-02-24 | Initial proposal — fix macOS sed compatibility |
| 2026-02-24 | Accepted and implemented. Scope expanded to 4 fixes per hook: (1) `\s` → `[[:space:]]` in sed, (2) trailing space in cd path capture, (3) git -C quoted/unquoted split, (4) initial detection regex for `git -C path commit` commands. All 8 test scenarios pass. |
