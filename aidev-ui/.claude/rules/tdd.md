# TDD Rules (Non-Negotiable)

- Write failing tests BEFORE implementation code. No exceptions.
- NEVER delete, comment out, skip, or weaken an existing test.
- "Weaken" means: changing exact assertions to range assertions, reducing assertion count,
  changing `toBe` to `toBeDefined`, adding `.skip`/`.todo`, wrapping in conditionals,
  or changing expected error types to generic errors.
- If a test seems wrong, FLAG IT for developer review. Do not change it yourself.
- Test BEHAVIOR (observable output for given input), not implementation details.
- Test the public API, not internal functions.
- One test at a time: write one failing test -> implement -> green -> next test.
- After completing a task, self-audit: re-read the feature brief and list any
  unaddressed acceptance criteria.

## Visual Testing Rules

- Storybook stories are acceptance tests. They are frozen during implement phase.
- NEVER modify a Storybook story during implement unless the reviewer approves.
- Visual regression baselines (screenshots) are part of the test snapshot.
- Accessibility tests (axe-core assertions) are first-class tests — same freeze rules apply.
- If a visual test seems wrong (story renders incorrectly), FLAG IT. Do not adjust the story.

## Test Ordering for UI Features

1. Write Storybook stories first (visual acceptance tests)
2. Write functional tests (React Testing Library)
3. Write a11y assertions (axe-core, keyboard navigation)
4. ALL must fail before implementation begins
