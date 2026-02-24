---
id: AIPIP-0009
title: Rename plans/ to AIPIP/ and /plan to /dev
status: accepted
created: 2026-02-24
created-by: claude
---

# AIPIP-0009: Rename plans/ to AIPIP/ and /plan to /dev

## Problem

Two naming issues:

1. **`plans/` folder** — Contains AIPIPs (AI Process Improvement Proposals) but is generically named `plans/`. The folder name should match its content.

2. **`/plan` command** — Conflicts with Claude Code's built-in `/plan` command (which toggles plan mode). Our `/plan` is a structured development workflow (specify → design → decompose → implement → complete) that handles everything from requirements gathering to shipping. It's not just "planning." The name also undersells the scope — it handles full projects, not just features.

## Proposal

### 1. Rename `plans/` → `AIPIP/`

Move the directory and update all references. The folder contains only AIPIP documents and `README.md` — the name should reflect that.

### 2. Rename `/plan` skill → `/dev`

- Rename `.claude/skills/plan/` → `.claude/skills/dev/`
- Update `SKILL.md` inside to reflect the new command name
- Update all hook scripts and rules that reference `/plan`

**Why `/dev`:** Short (3 chars), scope-neutral (works for a bug fix or a complex project), describes the activity (starting structured development). Doesn't imply a single phase like "plan" does.

## Impact

### Directory rename

| From | To |
|------|-----|
| `plans/` | `AIPIP/` |
| `.claude/skills/plan/` | `.claude/skills/dev/` |

### Files requiring `plans/` → `AIPIP/` reference updates

| File | References |
|------|------------|
| `CLAUDE.md` | AIPIP registry links, process governance references |
| `.claude/rules/process-governance.md` | `plans/` path in AIPIP instructions, `plans/README.md` |
| `.claude/hooks/process-guard.sh` | `plans/AIPIP-*.md` and `plans/README.md` allow-list |
| `README.md` | Any `plans/` references |
| `docs/knowledge-strategy.md` | Any `plans/` references |
| `memory/MEMORY.md` | AIPIP path references |

### Files requiring `/plan` → `/dev` reference updates

| File | References |
|------|------------|
| `.claude/skills/plan/SKILL.md` → `.claude/skills/dev/SKILL.md` | Skill definition (rename + content) |
| `.claude/skills/review/SKILL.md` | References to `/plan` workflow |
| `.claude/hooks/phase-gate.sh` | "Use /plan to continue" messages |
| `.claude/hooks/tdd-guard.sh` | "Use /plan to continue" message |
| `.claude/hooks/pre-commit-spec-warning.sh` | "using /plan to structure" message |
| `.claude/hooks/workflow-nudge.sh` | "suggest using /plan" message |
| `.claude/hooks/review-gate.sh` | "/plan" reference |
| `.claude/rules/development-workflow.md` | Not directly — references phases, not the command |

### Self-referencing AIPIP files (update path references only)

Existing AIPIPs in `plans/` reference `plans/README.md` and `plans/` paths internally. After the move these become `AIPIP/README.md` etc. These are historical documents — update only path references, not content.

## Alternatives Considered

### A. `/workflow` instead of `/dev`
Clear but long (9 chars). Typing `/dev` is faster for a frequently-used command.

### B. `/build` instead of `/dev`
Could be confused with compilation/CI builds.

### C. Keep `plans/` and just rename the command
The folder name `plans/` is misleading — it only contains AIPIPs, not feature plans. Both renames are worth doing together.

### D. `aipips/` (lowercase with s)
User explicitly preferred `AIPIP` — uppercase, no plural.

## Change Log

| Date | Change |
|------|--------|
| 2026-02-24 | Initial proposal |
| 2026-02-24 | Accepted and implemented. Moved `plans/` → `AIPIP/`, `.claude/skills/plan/` → `.claude/skills/dev/`. Updated 12 files: CLAUDE.md, process-governance.md, process-guard.sh, README.md, knowledge-strategy.md, MEMORY.md, phase-gate.sh, tdd-guard.sh, pre-commit-spec-warning.sh, workflow-nudge.sh, review-gate.sh, review SKILL.md. |
