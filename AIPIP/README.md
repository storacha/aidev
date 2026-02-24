# AIPIPs — AI Process Improvement Proposals

This directory contains versioned proposals for improving the AI development process.

## What is an AIPIP?

An AIPIP (AI Process Improvement Proposal) is a formal document proposing a change to the AI development workflow — rules, skills, hooks, or conventions. It provides traceability for why the process is the way it is.

## AIPIP Format

Each proposal is a markdown file with a required YAML metadata header:

```
---
id: AIPIP-NNNN
title: Short descriptive title
status: proposed | accepted | rejected | superseded
author: @github-handle
created: YYYY-MM-DD
supersedes: AIPIP-NNNN (if applicable)
superseded-by: AIPIP-NNNN (if applicable)
---
```

### Required Sections

1. **Problem** — What's wrong with the current process?
2. **Proposal** — What should change?
3. **Alternatives Considered** — What else was evaluated?
4. **Impact** — Which rules/skills/hooks change?
5. **Change Log** — Dated entries tracking revisions

## Statuses

| Status | Meaning |
|--------|---------|
| `proposed` | Under discussion, not yet accepted |
| `accepted` | Approved and implemented (or ready to implement) |
| `rejected` | Reviewed and declined (kept for historical record) |
| `superseded` | Replaced by a newer AIPIP (link in metadata) |

Note: `done` is used for accepted proposals that have been fully implemented.

## Naming Convention

Files are named: `AIPIP-NNNN-short-slug.md` (e.g., `AIPIP-0001-knowledge-system-v2.md`)

Numbers are assigned sequentially and never reused.

## How to Propose a Change

### Solo (local-only)

1. Create `.claude/.process-change-token` containing the AIPIP ID
2. Write `AIPIP-NNNN-slug.md` with status `proposed`
3. Present to your Claude session for review
4. On acceptance: update status to `accepted`, implement changes, delete token

### Team (PR flow)

1. Branch from main in `aidev/`: `git checkout -b aipip/NNNN-slug`
2. Write `AIPIP/AIPIP-NNNN-slug.md` with status `proposed`
3. Create `.claude/.process-change-token` locally (gitignored — never pushed)
4. Implement the process changes on the branch
5. Delete the token locally
6. Push branch, open PR to `storacha/aidev`
   - PR includes: AIPIP doc (status: `proposed`) + implementation
7. Team reviews — comments, suggestions
8. Process owner approves PR
9. Before merge: author updates AIPIP status to `accepted` (final commit)
10. Squash-merge to main
11. Other devs: `cd aidev && git pull`

## Registry

| ID | Title | Status |
|----|-------|--------|
| AIPIP-0001 | Knowledge System v2 — Research-Backed Improvements | done |
| AIPIP-0002 | Workflow Gaps — Test Integrity, Completion Phase, Human Review | done |
| AIPIP-0003 | Iterative Review Feedback Loop with Agent Separation | done |
| AIPIP-0004 | AI Process Governance — Central Repo, AIPIPs, Distribution | accepted |
| AIPIP-0005 | Session Continuity and Process Enforcement Hooks | accepted |
| AIPIP-0006 | Context Isolation and Task Ordering Enforcement | accepted |
| AIPIP-0007 | Require AIPIP Before Any Process Change | accepted |
| AIPIP-0008 | Fix session-resume.sh Pipefail Bug | accepted |
| AIPIP-0009 | Rename plans/ to AIPIP/ and /plan to /dev | accepted |
| AIPIP-0010 | Fix sed regex macOS compatibility in hooks | accepted |
| AIPIP-0011 | Create storacha/aidev repo for team distribution | accepted |
