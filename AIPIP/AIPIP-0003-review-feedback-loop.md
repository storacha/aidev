---
id: AIPIP-0003
title: Iterative Review Feedback Loop with Agent Separation
status: done
created: 2026-02-20
created-by: alex
last-updated: 2026-02-20
updated-by: claude
---

# AIPIP-0003: Iterative Review Feedback Loop with Agent Separation

## Context

AIPIP-0002 established Phase 5 (completion) with human review after push but before PR creation. Discussion revealed this is suboptimal:

- Reviewing a branch without a PR has no inline comments, no discussion threads
- Chat-based review doesn't scale for large diffs
- The real concern ("many PRs get messy") is solved by a single draft PR with fixup commits

Research into Copilot agent, Devin, and Claude Code GitHub Actions confirms: **one draft PR, updated with fixup commits per review round, squash-and-merge at the end** is the industry standard for AI-iterative review.

Additionally, three capabilities are missing:
1. No feedback loop — human gives feedback, but no defined process for AI to act on it
2. No agent separation — the implementer shouldn't validate its own feedback or review its own fixes
3. No unfinished work detection — starting a new feature while a previous one awaits review feedback

## Design

### Phase 5 Flow (Revised)

```
Tests pass → /review (automated) → commit → push → create draft PR
→ Present PR link + deliverable table
→ Human reviews on GitHub
→ [Feedback loop until approved]
→ Squash and merge → close spec
```

### Feedback Loop (New)

```
Human leaves PR review comments
  ↓
Feedback Validator Agent (independent subagent):
  - Reads PR comments via `gh api`
  - Reads the code + spec (brief.md, acceptance criteria)
  - For each comment, classifies:
      ACTIONABLE: creates a task with clear fix description
      CONTRADICTS SPEC: pushes back with thorough explanation
      UNCLEAR: asks human to clarify on the PR
  - Posts validation summary as a PR comment
  ↓
Execution Agent (separate context):
  - Picks up validated tasks
  - Implements fixes
  - Runs tests (must still pass)
  - Pushes fixup commits (NEVER force-push)
  ↓
Code Reviewer Agent (existing /review, incremental):
  - Reviews only the new commits
  - Checks for regressions
  ↓
Posts summary comment on PR
→ Human uses "Changes since last review" → reviews delta
→ Repeat until approved
```

### Feedback Validator Pushback Rules

The validator can push back on feedback when:
- It contradicts an accepted acceptance criterion: "This conflicts with AC3 which states [X]. To change this behavior, the spec needs updating first."
- It would break an existing passing test: "Implementing this would fail test [name] because [reason]."
- It's architecturally incompatible with the design: "The current design uses [pattern]. This feedback requires [different pattern]. Want to revise the design?"

Pushback must always include:
1. What the feedback asks for
2. What it conflicts with (spec, test, or architecture)
3. A concrete suggestion: update the spec, or an alternative approach

If the human updates the spec after pushback, the validator accepts the new spec as source of truth.

### Git Strategy During Review

- **Never force-push** after first human review (breaks "changes since last review")
- **Fixup commits** per round: `git commit --fixup <original>` for traceability
- **Squash-and-merge** at the end for clean history
- Each round's commits are prefixed: `fixup! review round N: <description>`

### Unfinished Work Check

On `/plan` start, before tier detection:
1. Check `.specs/active/` — if non-empty: "You have unfinished work on `{feature}` (phase: `{phase}`). Resume, or archive it?"
2. Check for open draft PRs from previous features — "Branch `feat/{slug}` has an open draft PR. Continue the review cycle?"

## Implementation Tasks

| # | Task | File(s) | What changes |
|---|------|---------|-------------|
| 1 | Revert Phase 5 to draft PR flow | `.claude/rules/development-workflow.md` | Replace "push then review before PR" with "push + draft PR, review on PR" |
| 2 | Update `/plan` Step 6 to draft PR + feedback loop | `.claude/skills/plan/SKILL.md` | Full Step 6 rewrite with feedback loop steps |
| 3 | Add feedback validator review point | `.claude/skills/review/SKILL.md` | New "Review Point 4: Feedback Validation" section |
| 4 | Add unfinished work check to `/plan` entry | `.claude/skills/plan/SKILL.md` | New "Step 0" before tier detection |
| 5 | Add git strategy rules for review rounds | `.claude/rules/development-workflow.md` | Fixup commit rules, no force-push after review |
| 6 | Add GitHub link format to deliverable presentation | `.claude/rules/development-workflow.md` | Always include PR link + compare URL |

## Risks

- **Over-engineering the loop**: The feedback loop adds complexity. Mitigation: the loop is opt-in — if the human approves on first review, no loop executes.
- **Feedback validator false pushback**: Validator might incorrectly reject valid feedback. Mitigation: pushback requires thorough evidence, and the human can override by updating the spec.
- **Context loss across rounds**: Each agent starts fresh. Mitigation: all context is on the PR (comments, commits, spec files) — agents read from the PR, not from memory.

## Success Criteria

- [ ] Draft PR created automatically after Phase 4 completion
- [ ] PR link + deliverable table always presented to human
- [ ] Feedback validator reads PR comments and classifies each one
- [ ] Validator pushes back on spec-contradicting feedback with evidence
- [ ] Execution agent implements only validated tasks
- [ ] Fixes pushed as fixup commits (never force-push)
- [ ] Code reviewer reviews only incremental changes
- [ ] Unfinished work detected on `/plan` start
- [ ] Human can approve at any round to end the loop

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-02-20 | claude | Initial plan from review workflow design discussion |
| 2026-02-20 | alex | Approved for implementation |
