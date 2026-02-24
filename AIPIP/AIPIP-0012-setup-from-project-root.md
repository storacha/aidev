---
id: AIPIP-0012
title: Run /setup from project root, not from inside aidev
status: accepted
created: 2026-02-24
created-by: claude
---

# AIPIP-0012: Run /setup from Project Root

## Problem

The current `/setup` flow requires the peer to `cd aidev`, start `claude`, run `/setup`, then exit and restart `claude` from the parent directory. This is an unnecessary extra step — the peer should start `claude` from the project root and run `/setup` there.

## Proposal

1. Update `/setup` skill to run `./aidev/setup.sh` instead of `./setup.sh`
2. Remove the "restart Claude" instruction — the user is already at the project root
3. Update README.md to reflect the simpler flow: clone → run claude from root → /setup → done

## Impact

### Modified files

| File | Change |
|------|--------|
| `.claude/skills/setup/SKILL.md` | Run `./aidev/setup.sh`, remove restart instructions |
| `README.md` | Simplify quick start: no `cd aidev` step |
