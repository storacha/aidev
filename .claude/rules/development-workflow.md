# Development Workflow Rules

## Phase Ordering (Mandatory)
You MUST follow this sequence. NEVER skip a phase.
1. SPECIFY: Ask value questions, produce feature brief. No code, no design.
2. DESIGN: Explore codebase read-only, produce design notes. No code, no tests.
3. DECOMPOSE + TEST: Break into tasks, write acceptance tests. Tests MUST fail.
4. IMPLEMENT: One task at a time, TDD red-green-refactor. Tests are FROZEN.
5. COMPLETE: Commit, push, draft PR. Human reviews on GitHub. Feedback loop until approved.

## Phase Constraints
- Phase 1-2: PLAN MODE ONLY. Do NOT create .ts/.js/.go/.py source files.
- Phase 3: You may ONLY create/modify test files (*test*, *spec*, *_test.go).
- Phase 4: Implement ONE task at a time. Do NOT start a blocked task. Tests are FROZEN (see below).

## Test Immutability (Phase 4)
During the implement phase, acceptance tests written in Phase 3 are frozen. You MUST NOT modify, delete, or rewrite test files. If you believe a test is incorrect or too strict:
1. STOP implementation of the affected task
2. Spawn a reviewer subagent (or use `/review`) with the specific test and your evidence
3. The reviewer decides: test bug vs implementation bug
4. If the reviewer confirms a test bug, it records the finding and the fix
5. Only THEN is the test modified — by the reviewer, not the implementer

Rationale: The implementer has an incentive to make tests pass. Tests are the spec. Modifying the spec to match the implementation inverts the TDD contract.

## Test Dispute Resolution
When a test fails and you believe the test itself is incorrect:
1. Document the evidence: which test, what it expects, why you think it's wrong, what the correct behavior should be
2. Spawn a reviewer subagent with this evidence and the relevant source code (test file + implementation file + any API/spec references)
3. The reviewer must independently verify by reading the source of truth (actual package exports, API signatures, specs)
4. Reviewer verdict:
   - **Test is wrong**: Reviewer modifies the test, documents the fix, implementation continues
   - **Implementation is wrong**: Implementer adjusts the implementation
   - **Ambiguous**: Escalate to user with both perspectives
5. Log the dispute to `.specs/telemetry.jsonl` for process improvement

## Before Each Task (Phase 4)
Re-read the task description from the feature brief AND the acceptance test.
Quote the acceptance criteria you are implementing. This prevents spec drift.

## Tier 0 Sanity Check
Even if the developer says "just do it," escalate to Tier 1 if the change:
- Touches more than 3 files
- Modifies a package in the blast radius table (CLAUDE.md)
- Changes a capability schema or shared interface
- Touches test infrastructure or CI config
Say: "This looks bigger than trivial because [reason]. Quick planning flow?"

## Stop-and-Redecompose Triggers
STOP implementation and re-decompose if:
- A task requires changing more than the planned 1-2 files
- You discover an undocumented dependency between tasks
- You need to modify a high-blast-radius package not in the plan
- A test reveals the Phase 2 interface design won't work
- You've attempted 3+ approaches for the same test failure
STOP means: do NOT commit in-progress changes. Report to the developer:
"Unexpected complexity: [description]. Current tasks need revision."

## Dependency Enforcement
Tasks use explicit dependency notation:
  - `[ ] Task 3 (after: 1, 2)` -- blocked by tasks 1 and 2
  - `[P] Task 4` -- independent, can run in any order
Before starting a task, verify ALL predecessor tasks are complete.
If predecessors are incomplete, work on an unblocked task instead.

## Mandatory Review Gates
Use AskUserQuestion to pause at EVERY phase transition:
- After Phase 1: "Here's the feature brief. Approve before I design?"
- After Phase 2: "Here's the design. Approve before I write tests?"
- After Phase 3: "Here are the tests (all failing). Approve before I implement?"
These gates are mandatory even in high-autonomy mode.

## Mandatory Code Review (End of Phase 4)
After ALL tasks are implemented and tests pass, run `/review --final {slug}`.
The review MUST be performed by a subagent (Task tool) for independent verification — never by the implementing agent in the same context.
This is enforced by `review-gate.sh` — the PHASE cannot transition to `complete` without `reviews/final.json`.
The review is a single pass covering all implementation changes.

## Completion Phase (Phase 5)
After all tests pass and the code review is done:
1. **Commit to a feature branch.** Branch name: `feat/{feature-slug}`. Only commit the deliverable files — not specs, tests, or analysis files.
2. **Push and create a draft PR.** Use `gh pr create --draft`. Include deliverable summary in the PR body (see format below).
3. **Present the PR link + deliverable summary** to the human:
   > **Draft PR ready for review:** {PR link}
   > **Compare:** https://github.com/{org}/{repo}/compare/main...feat/{feature-slug}
   >
   > | File | Status | Summary |
   > |------|--------|---------|
   > | `path/to/file` | New/Modified | One-line description |
   >
   > Acceptance tests: N/N passing. Automated review: passed.
   > Please review on GitHub. I'll address any feedback.
4. **Human reviews on GitHub.** They can leave inline comments, request changes, or approve.
5. **Feedback loop** (if human requests changes — see below).
6. **After approval + merge:** Move spec from `.specs/active/` to `.specs/done/`.

### Feedback Loop (Phase 5)
When the human leaves review comments on the PR:
1. **Feedback Validator Agent** (independent subagent) reads PR comments via `gh api`, reads the code + spec, and classifies each comment:
   - **ACTIONABLE**: Creates a task with clear fix description
   - **CONTRADICTS SPEC**: Pushes back with thorough explanation — what the feedback asks for, what it conflicts with, and a suggestion (update spec or alternative approach)
   - **UNCLEAR**: Posts a clarification question on the PR
2. **Execution Agent** (separate context) picks up validated tasks, implements fixes, runs tests, and pushes **fixup commits** (never force-push).
3. **Code Reviewer Agent** (existing `/review`) reviews only the new commits incrementally.
4. Posts a summary comment on the PR: "Addressed N items, pushed fixes."
5. Human uses GitHub's "Changes since last review" to review only the delta.
6. Repeat until human approves.

### Git Rules During Review
- **NEVER force-push** after the first human review (breaks "changes since last review")
- Use **fixup commits** per round for traceability: `review round N: <description>`
- **Squash-and-merge** at the end for clean history

### Feedback Validator Pushback Rules
The validator can push back when feedback:
- Contradicts an accepted acceptance criterion — cite the specific AC
- Would break a passing test — name the test and explain why
- Is architecturally incompatible — explain the conflict and suggest alternatives

Pushback must always include: (1) what the feedback asks, (2) what it conflicts with, (3) a concrete suggestion. If the human updates the spec, the validator accepts the new spec as source of truth.

### Deliverable Summary Format (PR Body)
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

## Spec Persistence
- Create `.specs/active/{feature-slug}/` at Phase 1 start
- Write brief.md, design.md, tasks.md as phases complete
- Move to `.specs/done/{feature-slug}/` after merge

## Hook Telemetry

When a hook blocks an action, append to `.specs/telemetry.jsonl`:
```json
{"event": "hook_block", "hook": "{hook-name}", "file": "{target-file}", "phase": "{current-phase}", "resolution": "adjusted|overridden|bug", "timestamp": "ISO8601"}
```

This data drives future hook tuning. If a hook blocks legitimate work >20% of the time, it needs adjustment.
