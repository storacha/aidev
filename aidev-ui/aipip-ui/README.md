# AIPIP-UI: AI Process Improvement Proposals (UI/Fullstack)

Process proposals for the `aidev-ui` fullstack development workflow. Parallel to `AIPIP/` (backend dev process) but fully independent.

## Format

Each proposal is a Markdown file with YAML metadata:

```yaml
---
id: AIPIP-UI-NNNN
title: Short descriptive title
status: proposed | accepted | rejected | superseded | done
author: @github-handle
created: YYYY-MM-DD
---
```

## Required Sections

1. **Problem** - What's broken or missing
2. **Proposal** - What to do about it
3. **Alternatives Considered** - What else was evaluated
4. **Impact** - What changes (files, hooks, rules, skills)
5. **Change Log** - Dated entries tracking status changes

## Status Lifecycle

`proposed` -> `accepted` -> `done`

Proposals can also be `rejected` or `superseded` by a newer AIPIP-UI.

## Registry

| ID | Title | Status |
|----|-------|--------|
| AIPIP-UI-0001 | Fullstack Development Workflow | proposed |
