Before the agent stops, verify that process state is consistent. Check these conditions:

1. **Uncommitted changes**: Run `git status --porcelain` in the project directory. If there are uncommitted changes AND a `.specs/active/*/PHASE` file exists with phase `implement`, warn that work may be lost.

2. **Task status**: If `.specs/active/*/tasks.md` exists, check if any tasks should be marked complete but aren't. Look for `[ ]` tasks where the corresponding test files might already pass.

3. **Phase staleness**: If the PHASE file says `implement` but all tests pass and all tasks appear done, suggest updating the phase to `complete`.

4. **Branch check**: If on `main`/`master` with uncommitted source file changes and an active feature, warn to create a feature branch.

If ALL conditions are clean, respond: `{"decision": "allow"}`

If ANY condition has issues, respond with:
```
{"decision": "block", "reason": "Brief description of what needs attention before stopping"}
```

Be concise. Do not perform fixes — just identify issues.
