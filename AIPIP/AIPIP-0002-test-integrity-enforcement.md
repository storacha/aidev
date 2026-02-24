---
id: AIPIP-0002
title: Workflow Gaps — Test Integrity, Completion Phase, Human Review
status: done
created: 2026-02-20
created-by: alex
last-updated: 2026-02-20
updated-by: claude
---

# AIPIP-0002: Workflow Gaps — Test Integrity, Completion Phase, Human Review

## Problem

During the first real use of the `/plan` workflow (feature: ucn-privacy-developer-docs), three structural gaps were discovered:

### Gap A: Implementer can modify tests

The implementing agent encountered 3 failing acceptance tests (AC6 import validation). Rather than escalating, the agent directly edited `test_acceptance.py` to fix what it believed were test bugs — and it happened to be right, but that's beside the point.

1. **No rule prevents it.** The development-workflow rules say Phase 3 = "only test files" and Phase 4 = "implement one task at a time." Nothing says "don't touch the tests in Phase 4."
2. **No hook prevents it.** The phase-gate hook has `implement) # All files allowed` — including test files.
3. **No independent review.** The agent made a unilateral judgment call that the tests were wrong. No second opinion was sought. The agent was both implementer and judge.

This is a conflict of interest. If the implementer can modify the tests, they can make anything pass. The tests are the spec — they must be immutable during implementation unless an independent party agrees they're wrong.

### Gap B: No completion phase defined

After implementation + review, the agent had no defined next steps. It just asked "what next?" instead of presenting the defined completion workflow. The workflow rules say "move to `.specs/done/` after merge" but don't cover anything between "tests pass" and "merge."

Missing steps:
1. Commit to a feature branch
2. Push and create a draft PR
3. Human reviews at PR time (best review surface: diffs, rendered previews, CI)
4. Move spec to `.specs/done/` after merge

### Gap C: Human review happens at wrong point

The original draft proposed blocking before commit, but commits are cheap local checkpoints — not the right gate. Research (Copilot agent, Devin, headless Claude Code, industry consensus) shows the review gate belongs at **draft PR time**, where:

- GitHub renders diffs and markdown previews
- CI checks have run
- Team members can also see and comment
- The developer gets the best review surface

The agent should: commit → push → create draft PR → present PR link with deliverable summary → wait for human to review/merge.

## Root Cause Analysis

The workflow assumed good faith but didn't enforce separation of concerns or define post-implementation steps. Five gaps:

| Gap | Layer | Description |
|-----|-------|-------------|
| Missing rule | Rules | No rule says "tests are frozen during implement phase" |
| Missing hook | Hooks | Phase gate allows all files in implement phase |
| Missing escalation procedure | Rules | No defined process for "I think the test is wrong" |
| Missing completion phase | Rules | No defined steps between "tests pass" and "merge" |
| Review gate at wrong point | Rules | Human review belongs at draft PR, not before commit |

## Proposed Fix

### Fix 1: Rule — Tests Are Frozen During Implementation

Add to `development-workflow.md`:

> **Test Immutability (Phase 4)**
> During the implement phase, acceptance tests written in Phase 3 are frozen. You MUST NOT modify, delete, or rewrite test files. If you believe a test is incorrect or too strict:
> 1. STOP implementation of the affected task
> 2. Spawn a reviewer subagent (or use `/review`) with the specific test and your evidence
> 3. The reviewer decides: test bug vs implementation bug
> 4. If the reviewer confirms a test bug, it records the finding and the fix
> 5. Only THEN is the test modified — by the reviewer, not the implementer
>
> Rationale: The implementer has an incentive to make tests pass. Tests are the spec. Modifying the spec to match the implementation inverts the TDD contract.

### Fix 2: Hook — Block Test File Writes During Implement Phase

Update `phase-gate.sh` to block test file modifications during the implement phase:

```bash
implement)
  if [ $IS_TEST -eq 1 ]; then
    echo "BLOCKED: Phase is 'implement'. Test files are frozen." >&2
    echo "If you believe the test is wrong, use /review to get an independent assessment." >&2
    exit 2
  fi
  ;;
```

This is the mechanical enforcement. The rule tells the agent what to do; the hook prevents it from doing the wrong thing even if it ignores the rule.

### Fix 3: Escalation Procedure — "I Think The Test Is Wrong"

Add a defined procedure to `development-workflow.md`:

> **Test Dispute Resolution**
> When a test fails and you believe the test itself is incorrect:
> 1. Document the evidence: which test, what it expects, why you think it's wrong, what the correct behavior should be
> 2. Spawn a reviewer subagent with this evidence and the relevant source code (test file + implementation file + any API/spec references)
> 3. The reviewer must independently verify by reading the source of truth (actual package exports, API signatures, specs)
> 4. Reviewer verdict:
>    - **Test is wrong**: Reviewer modifies the test, documents the fix, implementation continues
>    - **Implementation is wrong**: Implementer adjusts the implementation
>    - **Ambiguous**: Escalate to user with both perspectives
> 5. Log the dispute to `.specs/telemetry.jsonl` for process improvement

### Fix 4: Reviewer Subagent Context

The reviewer subagent (from AIPIP-0001 D1) needs explicit guidance for test disputes. Add to the review skill:

> **Test Dispute Reviews**
> When asked to review a test dispute:
> - Read the test file and understand what it's checking
> - Read the source of truth (package exports, API signatures, actual code)
> - Do NOT take the implementer's word for it — verify independently
> - Your job is to protect test integrity while fixing genuine test bugs
> - Document your verdict with evidence

### Fix 5: Completion Phase — Defined Post-Implementation Steps

Add to `development-workflow.md` and the `/plan` skill:

> **Phase 5: Complete**
> After all tests pass and automated review (`/review`) is done:
> 1. **Commit to a feature branch.** Branch name: `feat/{feature-slug}`. Only commit the deliverable files — not specs, tests, or analysis files.
> 2. **Push and create a draft PR.** Use `gh pr create --draft`. Include a deliverable summary in the PR body (see Fix 6 format).
> 3. **Present the PR link** to the human with a deliverable summary table. The PR is the review surface — diffs, rendered previews, CI results.
> 4. **Wait for human to review and merge.** Do NOT merge autonomously.
> 5. **After merge:** Move spec from `.specs/active/` to `.specs/done/`.
>
> Rationale: Commits are cheap local checkpoints. The PR is where human review belongs — it provides the best review surface (rendered diffs, markdown previews, CI results, team visibility). Automated gates (tests, `/review` subagent) handle pre-commit quality; human review focuses on intent, accuracy, and architecture at PR time.

### Fix 6: Deliverable Summary in PR Body

The draft PR body must include a reviewable deliverable table. Format:

> ## Summary
> - [1-3 bullet points describing what was built and why]
>
> ## Deliverables
> | File | Status | Summary |
> |------|--------|---------|
> | `path/to/file.md` | New | Concept page: what encrypted KV storage is (~1100 words) |
> | `path/to/meta.json` | Modified | Added navigation entry |
>
> ## Test plan
> - [ ] All acceptance tests pass (N/N)
> - [ ] Automated review passed
>
> Generated with Claude Code

The same table is presented inline when sharing the PR link, so the human knows what to review.

## Implementation Tasks

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 1 | Add "Test Immutability" rule | `.claude/rules/development-workflow.md` | 5 min |
| 2 | Add "Test Dispute Resolution" procedure | `.claude/rules/development-workflow.md` | 5 min |
| 3 | Update phase-gate hook to block test writes in implement | `.claude/hooks/phase-gate.sh` | 5 min |
| 4 | Add test dispute guidance to reviewer skill | `.claude/skills/review/SKILL.md` | 5 min |
| 5 | Update `/plan` skill to mention test freeze in Phase 4 instructions | `.claude/skills/plan/SKILL.md` | 5 min |
| 6 | Add completion phase (Phase 5: commit → draft PR → human review) to workflow rules | `.claude/rules/development-workflow.md` | 5 min |
| 7 | Add completion phase + PR format to `/plan` skill | `.claude/skills/plan/SKILL.md` | 5 min |
| 8 | Add deliverable summary format to workflow rules | `.claude/rules/development-workflow.md` | 5 min |

Total: ~40 minutes. All are small, targeted changes.

## Risks

- **False positives**: The hook will block legitimate test updates during implementation (e.g., adding a new test for a discovered edge case). Mitigation: the escalation procedure provides a path through — spawn a reviewer, get approval, reviewer makes the change.
- **Reviewer overhead**: Every test dispute requires a subagent. Mitigation: test disputes should be rare if Phase 3 tests are well-written. The overhead is the point — it creates friction against casual test modification.
- **Completion phase overhead**: Adding another gate slows down trivial features. Mitigation: Tier 0 features can skip the formal completion phase (just commit directly). The gate is most valuable for Tier 1+ where multiple files are involved.
- **Draft PR before human sees anything**: The work is pushed before the human reviews it. Mitigation: it's a *draft* PR — nothing merges without explicit human approval. Automated gates (tests + `/review` subagent) have already caught objective issues pre-commit.

## Success Criteria

- [ ] Phase-gate hook blocks test file writes during implement phase
- [ ] Agent follows escalation procedure when it encounters a test it believes is wrong
- [ ] Reviewer subagent independently verifies test disputes before any test modification
- [ ] No test modifications occur without an independent review verdict logged
- [ ] Agent commits, pushes, and creates a draft PR with deliverable summary
- [ ] Agent presents the PR link and waits for human to review/merge (does NOT merge autonomously)
- [ ] Spec moves to `.specs/done/` after merge

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-02-20 | claude | Initial draft from workflow gap discovered during ucn-privacy-developer-docs feature |
| 2026-02-20 | alex | Added Gap B (no completion phase) and Gap C (no human review with links) from same feature |
| 2026-02-20 | claude | Revised Fix 5/6: human review gate moved from "before commit" to "at draft PR time" (Option C). Based on research into Copilot agent, Devin, Claude Code headless, and industry consensus. Status → approved. |
| 2026-02-20 | alex | Final decision: review gate at "after push, before PR creation." Devs review the pushed branch first, then PR is created after approval. Can shift to PR-time later. |
