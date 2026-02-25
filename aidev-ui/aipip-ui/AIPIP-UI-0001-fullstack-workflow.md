---
id: AIPIP-UI-0001
title: Fullstack Development Workflow
status: accepted
author: @prodalex
created: 2026-02-25
---

# AIPIP-UI-0001: Fullstack Development Workflow

## Problem

The existing `aidev` development process (`/dev` skill) is optimized for backend work: UCAN capabilities, Go/JS services, cross-repo changes. It has no concept of visual design, design tokens, component libraries, Storybook, visual regression testing, accessibility validation, or Figma integration.

When building UI + backend features (fullstack), the backend process either:
- Gets in the way (hooks don't understand visual-design phases)
- Misses critical UI quality gates (no visual regression, no a11y checks)
- Doesn't leverage available AI-design tooling (Figma MCP, Storybook MCP, Playwright MCP)

A separate, purpose-built process is needed that runs independently without interfering with backend workflows.

## Proposal

Create `aidev-ui/` as a fully self-contained parallel process with:

### 6-Phase Workflow

| Phase | Name | Purpose | Allowed Files |
|-------|------|---------|---------------|
| 1 | **specify** | Value questions + visual requirements (Figma links, a11y, responsive breakpoints) | Markdown only |
| 2 | **visual-design** | Design tokens, Figma review, Storybook setup, component architecture | Markdown + design config (JSON/CSS tokens) |
| 3 | **design** | Technical design, API integration, data flow | Markdown only |
| 4 | **decompose** | Task breakdown + acceptance tests (including visual regression + a11y tests) | Test files + Storybook stories only |
| 5 | **implement** | TDD + visual verification loop (Playwright MCP screenshots) | Source files (tests frozen) |
| 6 | **complete** | Commit, PR, human review loop | No new files |

### Key Differences from Backend Process

1. **New phase: visual-design** (Phase 2) — establishes the visual foundation before technical design
2. **Design token pipeline** — W3C DTCG format tokens extracted from Figma, transformed to CSS/Tailwind
3. **Storybook-driven development** — components built in isolation with stories as living documentation
4. **Visual regression testing** — Storybook snapshots + Chromatic baselines as acceptance tests
5. **Accessibility as a first-class gate** — a11y tests included in acceptance criteria
6. **MCP integrations** — Figma MCP (read designs), Storybook MCP (component manifest), Playwright MCP (visual verification)
7. **Visual verification loop** — AI generates code, screenshots via Playwright, compares against Figma design, self-corrects

### Separation Guarantees

- `aidev-ui/` is fully self-contained (own .claude/, .specs/, CLAUDE.md, hooks, rules, skills)
- No references to `aidev/` files or directories
- No modifications to `aidev/` process files
- When symlinked into a project via `setup.sh`, creates independent `.claude`, `CLAUDE.md`, `.specs` symlinks
- Cannot coexist with `aidev/` in the same project (symlinks would conflict) — choose one per project

## Alternatives Considered

### A: Extend existing /dev with workflow type marker
- Add `WORKFLOW=fullstack` file to `.specs/active/{feature}/`
- Modify existing hooks to check workflow type
- **Rejected:** Violates "don't mix processes" principle. Complicates existing hooks. Risk of regressions in backend workflow.

### B: Minimal overlay (only add UI-specific hooks)
- Keep using `/dev` but add UI-specific hooks and rules
- **Rejected:** Phase structure doesn't fit (no visual-design phase). Would require invasive modifications to `/dev` skill.

### C: Fork aidev entirely
- Copy all of aidev/ and modify for UI
- **Rejected:** Too much duplication of backend-specific content (Go rules, UCAN capabilities, blast radius tables). Creates maintenance burden.

### D: Self-contained parallel process (chosen)
- New `aidev-ui/` with only what's needed for UI work
- Independent hooks, rules, skills
- No dependencies on aidev/
- **Chosen:** Clean separation, no risk to backend process, purpose-built for UI.

## Impact

### New Files
```
aidev-ui/
├── aipip-ui/
│   ├── README.md
│   └── AIPIP-UI-0001-fullstack-workflow.md
├── .claude/
│   ├── hooks/          (10 shell scripts)
│   ├── rules/          (6 markdown files)
│   ├── skills/         (3 skill directories)
│   └── settings.json
├── .specs/
│   ├── active/.gitkeep
│   ├── done/.gitkeep
│   ├── TEMPLATE-feature-brief.md
│   └── TEMPLATE-design-doc.md
├── CLAUDE.md
├── setup.sh
└── README.md
```

### Modified Files
None. The existing `aidev/` process is untouched.

### Risk
Low. Purely additive — new directory alongside existing code. No modifications to any existing files.

## Change Log

- 2026-02-25: Created as `proposed`
- 2026-02-25: Accepted by user, implementing
