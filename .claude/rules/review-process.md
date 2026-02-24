# Review Process Rules

## Mandatory Review
- After ALL Phase 4 tasks are complete: Run `/review --final {slug}` before transitioning to Phase 5
- This is enforced by `review-gate.sh` — the PHASE file cannot change to `complete` without `reviews/final.json`

## Review Behavior
- Reviews are non-blocking recommendations — the user decides whether to act on them
- Never skip the final review to save time
- If a review flags FAIL, present the issues to the user before proceeding
- NEEDS_ATTENTION items should be mentioned but don't block progress

## Context Isolation (Mandatory)
- The code review MUST be performed by a subagent (Task tool) — NEVER by the implementing agent in the same context
- The reviewer subagent starts fresh — pass explicit file paths and content, not "see above"
- This ensures independent verification: the reviewer is not influenced by implementation reasoning
- Keep reviewer prompts under 500 words for optimal instruction following

## What Does NOT Require a Separate Review
- Phase 3 tests — human approves tests at the review gate
- Individual tasks during Phase 4 — one final review covers everything
- Phase 5 PR — only reviewed by human on GitHub (feedback loop if needed)
