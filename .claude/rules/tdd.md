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
  unaddressed acceptance criteria. If any in-scope criteria are unaddressed,
  go back and add tests + implementation before proceeding.
