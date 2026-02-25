---
name: review
description: "Review implementation changes against conventions, design system, tests, accessibility, and feature brief"
user_invocable: false
---

# Code Review Skill (Fullstack UI)

This skill launches an independent code reviewer subagent to verify implementation against acceptance criteria, UI conventions, and accessibility requirements.

## Final Code Review (`--final <feature-slug>`)

**Trigger:** After all Phase 5 tasks are complete, before Phase 6 transition.
**Enforced by:** `review-gate.sh` hook (requires `reviews/final.json`).

### Subagent Receives:
- Feature brief (`brief.md`) — acceptance criteria
- Task list (`tasks.md`)
- Test files (from `tests-snapshot/`)
- Full git diff of all implementation changes
- UI conventions from `.claude/rules/conventions.md`

### Review Checklist

1. **SCOPE:** Changed files match task plans? Flag scope creep.
2. **CONVENTIONS:** Component naming (PascalCase), file structure, import ordering, TypeScript strict mode.
3. **DESIGN TOKENS:** No hardcoded colors, spacing, or typography. All values via tokens/Tailwind.
4. **ACCESSIBILITY:** Semantic HTML, ARIA attributes, keyboard navigation, contrast compliance.
5. **RESPONSIVE:** Mobile-first breakpoints, layout works across screen sizes.
6. **STORYBOOK:** All component states have stories. Stories match visual design.
7. **TEST INTEGRITY:** Any acceptance tests weakened? (compare against snapshot)
8. **COMPLETENESS:** Do changes fully implement all tasks + acceptance criteria?

### Output

Write `reviews/final.json`:
```json
{
  "type": "final",
  "feature": "{feature-slug}",
  "verdict": "pass" | "needs_attention" | "fail",
  "timestamp": "ISO8601",
  "summary": "One-line summary",
  "items": [
    {
      "category": "design_tokens|accessibility|conventions|scope|completeness",
      "severity": "info|warning|error",
      "description": "What was found",
      "file": "path/to/file",
      "suggestion": "How to fix"
    }
  ]
}
```

## Test Dispute Resolution

**Trigger:** Implementer stops work and calls `/review` with evidence a test is wrong.

1. Reviewer reads the test and the source of truth (component API, design, spec)
2. Verdict: test bug (reviewer modifies test) | implementation bug (implementer fixes) | ambiguous (escalate)
3. Log to `.specs/telemetry.jsonl`

## Feedback Validation (`--feedback <feature-slug> --pr <N>`)

**Trigger:** Human leaves review comments on draft PR.

1. Read PR comments via `gh api`
2. Classify each: ACTIONABLE | CONTRADICTS_SPEC | UNCLEAR
3. Post pushback on contradictory items with explanation
4. Return task list for execution agent
