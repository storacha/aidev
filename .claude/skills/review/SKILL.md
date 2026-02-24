---
name: review
description: "Review implementation changes against conventions, blast radius, tests, and feature brief"
user_invocable: false
---

# Code Reviewer Subagent

This skill launches a fresh-context verification subagent to review implementation code. It is called programmatically by the /dev workflow, not directly by the user.

## Arguments

Parse `$ARGUMENTS` for one of these modes:

- `--final <feature-slug>` -- Final code review after all tasks are implemented (before Phase 5)
- `--feedback <feature-slug> --pr <N>` -- Validate PR review feedback during Phase 5 feedback loop

If arguments are missing or malformed, report the error and stop.

---

## Review Point 1: Final Code Review

**Trigger:** `--final <feature-slug>`

**When:** After all Phase 4 tasks are complete, before transitioning to Phase 5 (complete). The `review-gate.sh` hook enforces this — the PHASE file cannot transition from `implement` to `complete` without the review artifact.

### 1. Gather Context

Read these files:
- `.specs/active/{feature-slug}/brief.md` -- the feature brief with acceptance criteria
- `.specs/active/{feature-slug}/tasks.md` -- the task list
- All test files in `.specs/active/{feature-slug}/tests-snapshot/` -- the original acceptance tests

Then collect the implementation diff:
- Determine the target repo from the brief/tasks
- Run `git diff HEAD` in that repo to get all uncommitted changes
- If changes are already committed on a feature branch, use `git diff main...HEAD`

### 2. Check for Test Weakening

Compare current test files against their snapshots in `.specs/active/{feature-slug}/tests-snapshot/`:
- Run a diff between each test file and its snapshot counterpart
- Flag ANY of these changes as test weakening:
  - Deleted or commented-out test cases
  - `.skip` or `.todo` added to tests
  - Exact assertions changed to range/loose assertions
  - Reduced assertion count
  - Changed expected error types to generic errors
  - Wrapped assertions in conditionals

### 3. Launch Subagent

Use the **Task tool** with `subagent_type: "general-purpose"` to launch a reviewer subagent. The subagent prompt must contain:

**Prompt structure (keep under 500 words):**

```
You are a code reviewer. Review the full implementation of a feature for quality and correctness.

## Feature Brief (summary)
{paste the Problem and Acceptance Criteria sections from brief.md}

## Tasks Implemented
{list all tasks from tasks.md with their planned file scopes}

## Test Snapshot Diff
{any differences between current tests and tests-snapshot/, or "No test modifications detected"}

## Code Diff
{paste the full git diff output}

## Conventions Reference
{paste relevant rules from .claude/rules/ files: naming, imports, error handling}

## Your Review Checklist
1. SCOPE: Do changed files match the task plans? Flag any files changed that are NOT in any task's planned scope (scope creep).
2. BLAST RADIUS: Are any high-blast-radius packages modified (@ucanto/core, @ucanto/interface, @storacha/capabilities, go-ucanto, go-libstoracha)? If so, was this explicitly planned?
3. CONVENTIONS: Does the code follow naming (kebab-case JS files, snake_case Go), import order (@storacha/* vs @web3-storage/* vs @ucanto/*), and error handling (Result<T,X> pattern) conventions?
4. TEST INTEGRITY: Were any acceptance tests weakened? (See Test Snapshot Diff above)
5. COMPLETENESS: Does the diff fully implement all tasks and address all acceptance criteria?

## Output Format
Respond EXACTLY in this format:

## Review: Code Review -- {feature-slug}
### PASS / FAIL / NEEDS_ATTENTION
- [x] Check description (passed)
- [ ] ATTENTION: issue description
- [ ] FAIL: issue description
### Comments
- Specific line-level feedback referencing diff line numbers
```

### 4. Write Review Artifact

**MANDATORY:** After the subagent returns, write a review artifact to `.specs/active/{feature-slug}/reviews/final.json`:

```json
{
  "type": "final",
  "feature": "{feature-slug}",
  "verdict": "pass" | "needs_attention" | "fail",
  "timestamp": "ISO8601",
  "summary": "One-line summary of the review outcome"
}
```

Create the `reviews/` directory if it doesn't exist. This artifact is checked by the `review-gate.sh` hook — the PHASE file cannot transition from `implement` to `complete` without it.

### 5. Present Results

After the subagent returns its review, present the output to the user verbatim. Prefix it with:

> **Automated Code Review** (final review -- independent reviewer):

If the review result is **FAIL**, explicitly tell the user:
> "The reviewer flagged issues with the implementation. Please review before proceeding to Phase 5."

If **NEEDS_ATTENTION**, mention the items but note they are non-blocking.

If **PASS**, note the clean review and proceed to Phase 5.

---

## Review Point 2: Test Dispute Resolution

**Trigger:** Called by the implementer when they believe an acceptance test is incorrect during Phase 4.

### Context Provided
The implementer provides:
- The specific test and what it expects
- Evidence for why they believe it's wrong
- The relevant source code (test file + implementation file + API/spec references)

### Review Behavior
- Read the test file and understand what it's checking
- Read the source of truth (package exports, API signatures, actual code)
- Do NOT take the implementer's word for it — verify independently
- Your job is to protect test integrity while fixing genuine test bugs

### Verdict
- **Test is wrong**: Modify the test, document the fix with evidence, implementation continues
- **Implementation is wrong**: Tell the implementer to adjust the implementation
- **Ambiguous**: Escalate to user with both perspectives

### Logging
Log the dispute to `.specs/telemetry.jsonl`:
```json
{"event": "test_dispute", "feature": "{feature-slug}", "test": "{test-name}", "verdict": "test_bug|impl_bug|ambiguous", "timestamp": "ISO8601"}
```

---

## Review Point 3: Feedback Validation (PR Review Comments)

**Trigger:** `--feedback <feature-slug> --pr <N>` -- Called during the Phase 5 feedback loop when the human has left PR review comments.

### 1. Gather Context

- Fetch PR review comments via `gh api repos/{org}/{repo}/pulls/{number}/reviews` and `gh api repos/{org}/{repo}/pulls/{number}/comments`
- Read `.specs/active/{feature-slug}/brief.md` — acceptance criteria are the source of truth
- Read the relevant source files mentioned in the comments

### 2. Launch Subagent

Use the **Task tool** with `subagent_type: "general-purpose"` to launch a feedback validator subagent.

**Prompt structure (keep under 500 words):**

```
You are an independent feedback validator. Your job is to assess human review feedback
for correctness and actionability before it gets implemented.

## Acceptance Criteria (source of truth)
{list each AC from brief.md, numbered}

## PR Review Comments
{for each comment: author, file, line, body}

## Relevant Code
{snippets of code referenced by comments}

## Your Task
For EACH review comment, classify it:

1. ACTIONABLE — The feedback is valid, clear, and can be implemented without
   contradicting the spec. Create a task:
   - What to change
   - Which file(s)
   - Expected outcome

2. CONTRADICTS_SPEC — The feedback asks for something that conflicts with an
   accepted acceptance criterion or architectural decision. Push back:
   - What the feedback asks for
   - Which AC or design decision it conflicts with
   - Why implementing it would break the contract
   - Suggestion: "To make this change, AC{N} would need to be updated first.
     Want to revise the acceptance criteria?"

3. UNCLEAR — The feedback is ambiguous or needs more context. Draft a
   clarification question to post on the PR.

## Output Format
For each comment:
### Comment: "{first 50 chars of comment}..."
**Classification:** ACTIONABLE / CONTRADICTS_SPEC / UNCLEAR
**Rationale:** {why this classification}
**Action:** {task description / pushback text / clarification question}

### Summary
- ACTIONABLE: N items → ready for execution agent
- CONTRADICTS_SPEC: N items → pushback posted
- UNCLEAR: N items → clarification requested
```

### 3. Post Results to PR

For CONTRADICTS_SPEC items, post a reply on the specific PR comment thread explaining the conflict. Be respectful and thorough — the human may have context the validator doesn't.

For UNCLEAR items, post a clarification question on the PR comment thread.

For ACTIONABLE items, return the task list to the orchestrator for the execution agent.

---

## Error Handling

- If `.specs/active/{feature-slug}/` does not exist, report: "No active spec found for '{feature-slug}'. Is the feature slug correct?"
- If `brief.md` is missing, report: "Feature brief not found. Run /dev to create a spec first."
- If the Task tool / subagent fails, report the error and suggest the user run a manual review.
