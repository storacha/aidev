---
name: dev
description: "Start the structured development workflow: specify, design, decompose, implement, complete"
user_invocable: true
---

# Unified Development Workflow: Lean PRD + SDD + TDD

This skill orchestrates the full Specify -> Design -> Decompose -> Implement workflow for any feature request. It auto-detects complexity, asks value-first questions, produces spec artifacts, writes acceptance tests before implementation, and enforces TDD throughout.

## Entry Point

When invoked, you receive the user's feature request as `$ARGUMENTS`. Your first job is to check for unfinished work, then classify the complexity tier.

## Step 0: Unfinished Work Check

Before starting any new feature, check for existing in-progress work:

1. **Check `.specs/active/` for active specs.** If any feature directory exists (not just `.gitkeep`):
   - Read the `PHASE` file to determine current phase
   - If phase is `implement` or earlier: "You have unfinished work on `{feature}` (phase: `{phase}`). Resume this feature, or archive it first?"
   - If phase is `complete`: "Feature `{feature}` has a draft PR awaiting review. Check the PR for feedback before starting new work."
   - Do NOT proceed to a new feature until the user explicitly says to archive or continue.

2. **Check for open draft PRs with pending feedback.** Run `gh pr list --draft --author @me` in the target repo. If any draft PRs exist for previous features:
   - "Draft PR #{number} (`{title}`) has unresolved review comments. Address the feedback first, or proceed with a new feature?"

This prevents abandoned features and ensures feedback loops get closed.

## Step 1: Tier Detection

Analyze the request and classify into one of four tiers:

### Tier 0: Trivial (Just Do It)
- Typo fix, config value change, one-line fix, formatting
- Touches 1-2 files max
- No behavioral change
- **Action:** Implement directly, show diff. No spec needed.
- **But first:** Run the Tier 0 Sanity Check (below).

### Tier 1: Quick (2-3 min planning)
- Bug fix with known cause, small well-scoped change
- Touches 2-5 files
- Single clear behavior change
- **Action:** Quick value questions -> Feature brief -> Skip Design -> Decompose -> Implement

### Tier 2: Standard (5-10 min planning)
- New feature, significant enhancement
- Touches 5-15 files
- Multiple related behavior changes
- **Action:** Full value questions -> Feature brief -> Design -> Decompose -> Implement

### Tier 3: Full (15-25 min planning)
- Architectural change, cross-service modification, new capability
- Touches 10+ files across multiple packages/services
- **Action:** Full value + scope questions -> Feature brief -> Design doc -> Decompose -> Implement

**Present your tier assessment to the user:**
> "This looks like a **Tier [N]** ([label]) change because [reason]. I'll [describe the process]. Sound right?"

If the user disagrees, adjust. They know their codebase better than you.

### Telemetry: Log Tier Selection
Append to `.specs/telemetry.jsonl`:
```json
{"event": "tier_selected", "feature": "{feature-slug}", "tier": N, "timestamp": "ISO8601"}
```

## Tier 0 Sanity Check

Even if the user says "just do it," **escalate to Tier 1** if the change:
- Touches more than 3 files
- Modifies a package in the blast radius table (check CLAUDE.md)
- Changes a capability schema or shared interface
- Touches test infrastructure or CI config

Say: "This looks bigger than trivial because [reason]. Quick planning flow?"

If Tier 0 is confirmed, implement directly and stop. The remaining steps are for Tier 1+.

## Step 2: PHASE 1 — SPECIFY (Value-First Questioning)

### Create the spec directory
Create `.specs/active/{feature-slug}/` and write `PHASE` file:
```
echo "specify" into .specs/active/{feature-slug}/PHASE
```

The feature slug should be a kebab-case version of the feature name (e.g., `add-blob-encryption`).

### Ask value questions

**All tiers (Tier 1+):**
1. **What problem does this solve?** (What's broken/missing, and for whom?)
2. **Who benefits?** (End users? Developers? Operators?)
3. **What does success look like?** (Measurable outcome — how will we know it works?)
4. **What's the time appetite?** (How much time should we spend? "2 days" / "1 week" / "2 weeks")

**Tier 2+ additional questions:**
5. **What's the simplest version?** (If we had to ship in half the time, what would we cut?)
6. **What should we NOT build?** (Explicit no-gos to prevent scope creep)
7. **Known rabbit holes or risks?** (Where might we get stuck?)
8. **Existing patterns to follow?** (AI: search the codebase for similar implementations)

**Smart questioning rules:**
- Skip questions you can answer from context. If the user already explained the problem, don't re-ask.
- For question 8, proactively search the codebase yourself. Use Grep/Glob to find similar patterns, then present what you found: "I found [pattern] in [file]. Should we follow this approach?"
- Be conversational, not form-filling. Weave questions naturally.
- If the user provides a detailed description upfront, extract answers and confirm: "Based on what you said, here's what I understand: [summary]. Anything to add?"

### Produce the Feature Brief

Using the template at `.specs/TEMPLATE-feature-brief.md`, create `.specs/active/{feature-slug}/brief.md`.

Fill in all sections. Acceptance criteria MUST be testable — each one should be convertible to a test assertion.

### Review Gate (MANDATORY)

Present the feature brief to the user and ask:
> "Here's the feature brief. Please review the acceptance criteria carefully — these become the tests that define 'done.' Approve before I move to design?"

**Do NOT proceed until the user approves.** If they request changes, update the brief and re-present.

After approval, update the phase:
```
echo "design" into .specs/active/{feature-slug}/PHASE
```

**Tier 1 shortcut:** Skip Phase 2 (Design). Update phase directly to `decompose` and proceed to Step 4.

## Step 3: PHASE 2 — DESIGN (Read-Only Exploration)

**Constraint: PLAN MODE ONLY. Do NOT create any .ts/.js/.go/.py files.**

### Design Activities
1. Read the feature brief
2. Explore the codebase in read-only mode:
   - Find the files that will need to change
   - Identify interfaces and data flows
   - Check for existing patterns to follow
   - Identify test infrastructure needs and mocking patterns
   - For Storacha repos: check the repo's CLAUDE.md for repo-specific patterns
3. Identify risks and dependencies

### Produce Design Notes

**Tier 2:** Add design notes as a `## Design Notes` section in `brief.md`:
- Files to change (with line references)
- Interfaces to implement/extend
- Data flow summary
- Test strategy (what testing patterns, mocks needed)

**Tier 3:** Create a separate `.specs/active/{feature-slug}/design.md` using the template at `.specs/TEMPLATE-design-doc.md`. This adds:
- Architecture diagram (text-based)
- Migration strategy
- Rollback plan
- Performance considerations

### Review Gate (MANDATORY)

Present the design to the user:
> "Here's the design. I've identified [N] files to change and [approach summary]. Approve before I write tests?"

**Do NOT proceed until the user approves.**

After approval, update the phase:
```
echo "decompose" into .specs/active/{feature-slug}/PHASE
```

## Step 4: PHASE 3 — DECOMPOSE + WRITE ACCEPTANCE TESTS

**Constraint: You may ONLY create/modify test files in this phase. No source files.**

### 4a. Task Decomposition

Break the plan into ordered tasks. Write to `.specs/active/{feature-slug}/tasks.md`:

Rules for tasks:
- **1-2 files per task**, completable in <4 hours of AI work
- **Independent tasks marked `[P]`** for potential parallel execution
- **Dependencies explicit:** `[ ] Task 3 (after: 1, 2)` means blocked by tasks 1 and 2
- Each task maps to a specific test file
- Update the feature brief's Tasks section to match

### 4b. Write Acceptance Tests

**CRITICAL: Use a subagent (Task tool) for test writing to prevent context pollution.**

The subagent should receive ONLY:
- The feature brief (brief.md)
- The acceptance criteria
- The repo's test patterns (from repo CLAUDE.md or existing test files)
- The file paths from the design notes

The subagent should NOT receive:
- Implementation details from Phase 2 exploration
- Specific code snippets from source files
- Your design reasoning about HOW to implement

This isolation prevents implementation knowledge from leaking into test design, which research shows degrades TDD quality.

For each acceptance criterion, create test files that:
- Follow existing test patterns in the repo (Mocha for JS, testify for Go)
- Test BEHAVIOR (observable output for given input), not implementation details
- Test the public API, not internal functions
- Are specific enough to define "done" for each task
- All FAIL when run (they are RED — the implementation doesn't exist yet)

### 4c. Create Test Snapshot

Copy all newly created test files to `.specs/active/{feature-slug}/tests-snapshot/`. This snapshot is used by the test-modification-detector hook during Phase 4 to flag if acceptance tests are being weakened.

### 4d. Write Subagent Attestation

After the subagent produces the test files and they are copied to the snapshot, write an attestation file to prove tests were written in isolation:

```json
// .specs/active/{feature-slug}/subagent-attestation.json
{
  "written_by": "subagent",
  "timestamp": "ISO8601",
  "test_files": ["list of test file paths produced"],
  "brief_hash": "first 8 chars of sha256 of brief.md content"
}
```

**This is enforced by `review-gate.sh`** — the PHASE cannot transition from `decompose` to `implement` without this file. If you skip the subagent and write tests directly, the hook will block you.

### 4e. Verify Tests Fail (Red Test Check)

Run the test suite and verify ALL new acceptance tests fail. If any test passes:
- The feature may already exist
- Or the test is vacuous (always passes)
- Investigate and fix before proceeding

### Review Gate (MANDATORY)

Present the task list and test files to the user:
> "Here are the acceptance tests (all failing/RED). These define 'done' for each task. Do these capture your intent? Approve before I implement?"

**This is the key review moment.** The developer reviews TESTS (intent), not code (implementation). No automated review at this gate — human approval is sufficient.

After approval, update the phase:
```
echo "implement" into .specs/active/{feature-slug}/PHASE
```

## Step 5: PHASE 4 — IMPLEMENT (TDD Red-Green-Refactor)

### Context Refresh
At the start of Phase 4, re-read:
- The feature brief (`brief.md`)
- The task list (`tasks.md`)
- All acceptance test files

This pushes Phase 2 exploration details out of active attention and re-centers on the test-defined targets.

### For Each Task (in dependency order)

1. **Check dependencies.** Read `tasks.md` and verify ALL predecessor tasks for the next task are marked with ✓. If predecessors are incomplete, work on an unblocked `[P]` task instead. **NEVER start a task whose dependencies are not complete.**

2. **Write CURRENT_TASK file.** Before starting work on a task, write the task number to the state file:
   ```
   echo "N" into .specs/active/{feature-slug}/CURRENT_TASK
   ```
   This allows the session-resume hook to inject which task is in progress if the session is interrupted. When a task is complete, update this file to the next task number (or delete it after the final task).

3. **Read the acceptance test.** Quote the acceptance criteria you are implementing:
   > "Implementing Task N: [description]. Acceptance criterion: [quoted from brief]."

4. **Write unit tests** for your specific implementation approach. These are more granular than acceptance tests — they test specific functions/methods. (RED)

5. **Implement minimal code** to pass all tests. (GREEN)
   - Write the simplest code that makes the tests pass
   - Do NOT over-engineer or add unrequested features

6. **Refactor** while keeping tests green. (REFACTOR)
   - Clean up code structure
   - Extract shared logic
   - Ensure naming follows codebase conventions

7. **Self-audit.** Produce a structured checklist:
   ```
   Acceptance Criteria Audit:
   - [x] Criterion 1: PASS — evidence: test_name in test_file.test.ts
   - [x] Criterion 2: PASS — evidence: test_name in test_file.test.ts
   - [ ] Criterion 3: FAIL — [reason]
   ```
   Then do a mechanical cross-check: for each acceptance criterion, grep the test files for a test that asserts on it. List any criteria with no matching test.

   If ANY in-scope criteria are unaddressed: go back to step 4 and add tests + implementation. Do NOT proceed.

8. **Run full test suite + lint + type-check.** Everything must pass.

9. **Mark task complete** in tasks.md (add ✓ to the task heading). Update `CURRENT_TASK` to the next task number. Move to next task.

### After ALL Tasks Complete — Mandatory Code Review

Once every task is marked ✓ in tasks.md, run a single code review covering all implementation changes.

**CRITICAL: The code review MUST be performed by a subagent** (Task tool) to ensure independent verification in a fresh context. The reviewing agent must NOT share context with the implementing agent. This is the same isolation principle as Phase 3 test-writing — the reviewer should assess the code without being influenced by implementation reasoning.

Launch the review subagent with:
- The feature brief (`brief.md`) — acceptance criteria are the success measure
- The test files — what passes/fails
- The git diff of all implementation changes
- Instructions to check: convention violations, scope creep, test weakening, blast radius

The subagent writes `reviews/final.json` with its verdict. The `review-gate.sh` hook enforces this — the PHASE cannot transition from `implement` to `complete` without the review artifact AND all tasks marked done.

Alternatively, invoke the review skill: `/review --final {feature-slug}` — which internally uses a subagent.

### Test Freeze (Phase 4)
Acceptance tests from Phase 3 are **frozen** during implementation. You MUST NOT modify, delete, or rewrite them. The phase-gate hook will block test file writes.

If you believe a test is wrong:
1. STOP the current task
2. Use `/review` or spawn a reviewer subagent with the test + your evidence
3. Only the reviewer can modify the test after independent verification
4. See "Test Dispute Resolution" in `.claude/rules/development-workflow.md`

### TDD Guards (Always Active)
- NEVER delete, comment out, skip, or weaken an existing test
- "Weaken" means: changing exact assertions to range assertions, reducing assertion count, changing `toBe` to `toBeDefined`, adding `.skip`/`.todo`, wrapping in conditionals, or changing expected error types to generic errors
- If a test seems wrong, FLAG IT for developer review. Do not change it yourself.
- Test BEHAVIOR, not implementation details
- One test at a time: write one failing test -> implement -> green -> next test

### Stop-and-Redecompose Triggers

STOP implementation and re-decompose if:
- A task requires changing more than the planned 1-2 files
- You discover an undocumented dependency between tasks
- You need to modify a high-blast-radius package not in the plan
- A test reveals the Phase 2 interface design won't work
- You've attempted 3+ approaches for the same test failure

STOP means: do NOT commit in-progress changes. Report to the developer:
> "Unexpected complexity: [description]. Current tasks need revision. Here's what I've learned: [findings]. Suggested re-decomposition: [new task breakdown]."

## Step 6: PHASE 5 — COMPLETE (Commit → Draft PR → Review Loop)

After all tasks are complete:

1. **Run the full test suite one final time.**

2. **Produce a final self-audit** against ALL acceptance criteria.

3. **Log completion telemetry.** Append to `.specs/telemetry.jsonl`:
   ```json
   {"event": "feature_complete", "feature": "{feature-slug}", "tier": N, "tasks": N, "phases_completed": ["specify", "design", "decompose", "implement", "complete"], "timestamp": "ISO8601"}
   ```

4. **Commit to a feature branch.** Branch name: `feat/{feature-slug}`. Only commit the deliverable files — not specs, tests, or analysis files.

5. **Push and create a draft PR.** Use `gh pr create --draft`. PR body format:

   ```
   ## Summary
   - [1-3 bullet points: what was built and why]

   ## Deliverables
   | File | Status | Summary |
   |------|--------|---------|
   | `path/to/file` | New/Modified | One-line description |

   ## Test plan
   - [ ] All acceptance tests pass (N/N)
   - [ ] Automated review passed

   Generated with Claude Code
   ```

6. **Present PR link + deliverable summary** to the human:

   > **Draft PR ready for review:** {PR URL}
   > **Compare:** https://github.com/{org}/{repo}/compare/main...feat/{feature-slug}
   >
   > | File | Status | Summary |
   > |------|--------|---------|
   > | `path/to/file` | New/Modified | One-line description |
   >
   > Acceptance tests: N/N passing. Automated review: passed.
   > Please review on GitHub. I'll address any feedback.

7. **Wait for human review.** The human reviews on GitHub (inline comments, request changes, or approve).

### Step 6a: Feedback Loop (if human requests changes)

When the human reports feedback (either in chat or by saying "check the PR comments"):

1. **Read PR comments.** Use `gh api repos/{org}/{repo}/pulls/{number}/reviews` and `gh pr view {number} --comments` to fetch all review comments.

2. **Launch Feedback Validator Agent** (independent subagent via Task tool). Pass it:
   - The PR comments
   - The feature brief (acceptance criteria)
   - The current code (relevant files)
   - Instructions to classify each comment as ACTIONABLE, CONTRADICTS_SPEC, or UNCLEAR

   The validator posts its assessment as a PR comment summarizing what will be addressed and any pushback.

3. **Launch Execution Agent** (separate subagent via Task tool) for validated tasks. It:
   - Implements fixes for ACTIONABLE items
   - Runs tests (must still pass)
   - Pushes **fixup commits** (NEVER force-push): `review round N: <description>`

4. **Launch Code Reviewer Agent** (`/review` in incremental mode) to review only the new commits.

5. **Post summary comment on PR:** "Addressed N items, pushed fixes. Please re-review."

6. **Present to human:** "I've addressed the feedback and pushed fixes. Check 'Changes since last review' on the PR."

7. **Repeat** from step 1 if human has more feedback. Loop ends when human approves.

### Git Rules During Feedback Loop
- **NEVER force-push** after first human review (breaks "changes since last review")
- Use **fixup commits** per round for traceability
- **Squash-and-merge** at the end for clean history

8. **After approval + merge:** Move spec from `.specs/active/{feature-slug}/` to `.specs/done/{feature-slug}/`. Update PHASE to `done`.

## Step 7: Retro Check

Count completed features in `.specs/done/`. If the count is a multiple of 5:

> "You've completed {N} features through this workflow. Time for a quick retro!"

Use the template at `.specs/RETRO-TEMPLATE.md`. Ask the 4 key questions:
1. Which phase felt most valuable? Least valuable?
2. Did any hook block you incorrectly? Which one?
3. Did the tier selection feel right, or did you override it?
4. What would make this faster?

Save responses to `.specs/retro-log.md` (append, don't overwrite).

## Autonomy Spectrum

Adjust review frequency based on the nature of the work:

- **High autonomy** (auto-accept mode): Peripheral features, routine changes, well-established patterns. Review at phase gates only.
- **Medium autonomy** (task-by-task review): Production features, moderate complexity. Review after each task.
- **Low autonomy** (interactive guidance): Security-sensitive code, shared packages, blast-radius changes. Review each significant decision.

The user can override at any time: "just go" (higher autonomy) or "walk me through it" (lower autonomy).

## Phase File Reference

The `.specs/active/{feature-slug}/PHASE` file contains one of these values:
- `specify` — Phase 1 in progress
- `design` — Phase 2 in progress
- `decompose` — Phase 3 in progress
- `implement` — Phase 4 in progress
- `complete` — Phase 5: committed + draft PR created, awaiting human review or in feedback loop
- `done` — Merged and moved to `.specs/done/`

Hooks use this file to enforce phase constraints. Only one active spec at a time.

### Other State Files

- **`CURRENT_TASK`** — Contains the task number currently being implemented (Phase 4 only). Written before starting each task, updated after completion. Used by `session-resume.sh` to inject task context on session boundaries.
- **`subagent-attestation.json`** — Written after Phase 3 test subagent completes. Required by `review-gate.sh` for decompose→implement transition.
- **`reviews/final.json`** — Written by the `/review --final` subagent. Required by `review-gate.sh` for implement→complete transition.

## Quick Reference: What Each Phase Produces

| Phase | Produces | Allowed File Types |
|-------|----------|--------------------|
| 1. Specify | `brief.md` | Markdown only (no source, no tests) |
| 2. Design | Design notes in `brief.md` or `design.md` | Markdown only (no source, no tests) |
| 3. Decompose | `tasks.md` + acceptance test files + `tests-snapshot/` + `subagent-attestation.json` | Test files only (no source) |
| 4. Implement | Source files + unit tests + `CURRENT_TASK` + `reviews/final.json` | All files except acceptance tests (frozen) |
| 5. Complete | Feature branch + draft PR + feedback loop | No new files — commit, PR, iterate until approved |
