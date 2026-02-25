---
id: AIPIP-0004
title: AI Process Governance — Central Repo, AIPIPs, Distribution
status: accepted
author: @alex
created: 2026-02-20
last-updated: 2026-02-20
updated-by: claude
supersedes: null
---

# AIPIP-0004: AI Process Governance — Central Repo, AIPIPs, Distribution

## Problem

The AI development process (rules, skills, hooks, workflow) currently lives in `storacha-analysis`, a research/analysis repo. This creates several problems:

1. **No governance**: Anyone with access can modify process files directly
2. **No contribution model**: Developers have no defined way to suggest process improvements
3. **No distribution**: Process files aren't shared across the 82 product repos
4. **No versioning**: Changes to the process aren't formally tracked or reviewed
5. **Naming**: "Plans" is generic — the process improvement proposals need a distinct identity

## Proposal

### 1. Central Repository: `storacha/ai-dev-process` (private)

```
storacha/ai-dev-process
├── CLAUDE.md                         # root instructions for the process
├── .claude/
│   ├── rules/                        # workflow rules (development-workflow.md, tdd.md, etc.)
│   ├── skills/                       # skills (plan, review, discover, etc.)
│   └── hooks/                        # phase-gate.sh, etc.
├── proposals/
│   ├── README.md                     # how to submit an AIPIP
│   ├── TEMPLATE.md                   # copy to start a proposal
│   ├── AIPIP-0001-knowledge-system-v2.md
│   ├── AIPIP-0002-test-integrity.md
│   ├── AIPIP-0003-review-feedback-loop.md
│   └── AIPIP-0004-process-governance.md
├── .github/
│   ├── CODEOWNERS
│   ├── ISSUE_TEMPLATE/
│   │   └── process-suggestion.md
│   └── PULL_REQUEST_TEMPLATE/
│       └── proposal.md
└── README.md                         # what this repo is, how to use it
```

### 2. Rename Plans → AIPIPs (AI Process Improvement Proposals)

| Old | New |
|-----|-----|
| `plans/PLAN-0001-*.md` | `proposals/AIPIP-0001-*.md` |
| "plan" | "AIPIP" (proposal) |
| Plan status lifecycle | `proposed` → `accepted` → `rejected` / `superseded` |

AIPIP format:
```markdown
---
id: AIPIP-NNNN
title: Short descriptive title
status: proposed | accepted | rejected | superseded
author: @github-handle
created: YYYY-MM-DD
supersedes: AIPIP-NNNN (if applicable)
superseded-by: AIPIP-NNNN (if applicable)
---

# AIPIP-NNNN: Title

## Problem
What's wrong with the current process?

## Proposal
What should change?

## Alternatives Considered
What else was evaluated?

## Impact
Which rules/skills/hooks change? Which repos are affected?
```

Numbers assigned sequentially. Rejected proposals stay for historical record.

### 3. Protection

| Mechanism | Scope | Bypassable? |
|-----------|-------|-------------|
| Branch protection on `main` | PR-only, no direct push, enforce_admins enabled | No |
| CODEOWNERS: `@storacha/aidev-owners` team | All changes require team member review | No |
| Pre-commit hook in product repos | Warns devs if they modify `.claude/shared/` | Yes, but server-side catches it |

CODEOWNERS file:
```
# All changes require approval from aidev-owners team
*                        @storacha/aidev-owners
```

### 4. Distribution (via git subtree)

Product repos pull the process into `.claude/shared/`:
```bash
# One-time setup:
git subtree add --prefix=.claude/shared \
  https://github.com/storacha/ai-dev-process.git main --squash

# Update:
git subtree pull --prefix=.claude/shared \
  https://github.com/storacha/ai-dev-process.git main --squash
```

Claude Code auto-discovers `.claude/rules/` via directory traversal, so shared rules are loaded automatically. Product repos keep their own repo-specific rules in `.claude/rules/` alongside.

### 5. Contribution Model

**Developers cannot directly edit process files.** Three contribution paths:

**Path A — Full AIPIP** (significant changes):
1. Fork/branch, copy `proposals/TEMPLATE.md` to `proposals/AIPIP-NNNN-slug.md`
2. Open PR to `ai-dev-process`
3. Discussion on the PR
4. Process owner approves → proposal merged → rule changes implemented

**Path B — Lightweight suggestion** (small ideas):
1. Open GitHub issue using "Process Suggestion" template
2. Process owner triages, promotes to AIPIP if warranted

**Path C — Local experimentation** (encouraged):
1. Developer uses `.claude/CLAUDE.local.md` (gitignored) for personal overrides
2. If experiment works, submit as AIPIP

### 6. What Stays in `storacha-analysis`

| In `ai-dev-process` (process) | In `storacha-analysis` (knowledge) |
|-------------------------------|-------------------------------------|
| CLAUDE.md (root instructions) | memory/ (tech knowledge, flows) |
| .claude/rules/ | data/ (scanner output) |
| .claude/skills/ | scripts/ (scanners) |
| .claude/hooks/ | tools/ (query tool) |
| proposals/ (AIPIPs) | research/ (reports) |
| | repos/ (cloned repos) |
| | .specs/ (active/done feature specs) |

The process repo governs HOW the AI works. The analysis repo contains WHAT the AI knows.

## Migration Plan

**Not now.** Keep iterating in `storacha-analysis` until the process is battle-tested on 2-3 real features. Then:

1. Create `storacha/ai-dev-process` (private)
2. Move process files (CLAUDE.md, .claude/rules, .claude/skills, .claude/hooks)
3. Rename plans/ → proposals/, PLAN → AIPIP
4. Set up branch protection + CODEOWNERS
5. Add issue/PR templates
6. Set up git subtree in first product repo as pilot
7. Write README with setup instructions

## Impact

- Renames: PLAN-0001 through PLAN-0003 → AIPIP-0001 through AIPIP-0003
- New repo: `storacha/ai-dev-process`
- New files: CODEOWNERS, issue template, PR template, proposals README, TEMPLATE
- Process files move out of `storacha-analysis`

## Alternatives Considered

- **Public repo**: Would let community benefit from novel patterns. Rejected for now — process is still evolving. Can open-source later.
- **GitHub team for process ownership**: Overkill for one person. Easy to add later.
- **Git submodule instead of subtree**: Subtree is simpler for consumers (no `git submodule update` required).
- **npm/go package for distribution**: Over-engineered for config files.

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-02-20 | claude | Initial proposal |
| 2026-02-20 | alex | Accepted: private repo, solo owner, migrate when stable |
