# Review Process Rules

## Mandatory Review
- After ALL Phase 5 tasks are complete: Run `/review --final {slug}` before transitioning to Phase 6
- This is enforced by `review-gate.sh` — PHASE cannot change to `complete` without `reviews/final.json`

## Review Checklist (UI-Specific)
In addition to standard code review, the reviewer checks:
1. **Design token usage** — no hardcoded colors, spacing, or typography
2. **Component structure** — follows project conventions (PascalCase, barrel exports)
3. **Accessibility** — semantic HTML, ARIA attributes, keyboard navigation
4. **Responsive design** — mobile-first, breakpoints work correctly
5. **Storybook stories** — all component states covered
6. **Visual consistency** — matches Figma design (if provided)

## Review Behavior
- Reviews are non-blocking recommendations — the user decides whether to act
- Never skip the final review to save time
- If a review flags FAIL, present the issues to the user before proceeding
- NEEDS_ATTENTION items should be mentioned but don't block progress

## Context Isolation (Mandatory)
- Code review MUST be performed by a subagent (Task tool)
- Never by the implementing agent in the same context
- Reviewer starts fresh — pass explicit file paths and content
- Keep reviewer prompts under 500 words
