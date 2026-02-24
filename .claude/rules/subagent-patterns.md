# When to Use Subagents

## Always use a subagent for:
- **Phase 3 acceptance test writing** — context isolation from Phase 2 design prevents implementation knowledge from leaking into tests
- **Phase 4 code review** (reviewer pattern from `/review` skill) — independent verification in fresh context
- **Cross-repo impact analysis** — explore multiple repos without polluting main conversation context
- **Research tasks** — web search, spec lookup, broad codebase exploration — keeps main context focused on the current task

## Consider a subagent for:
- Exploring an unfamiliar repo (use `/discover` skill via subagent)
- Blast radius investigation (check all downstream consumers of a package)
- Debugging complex failures (isolate investigation from fix attempts)
- Long-running searches that might return large results

## Do NOT use a subagent for:
- Simple file reads or searches (use Grep/Glob directly — faster, less overhead)
- Single-file edits with clear instructions
- Tasks requiring main conversation context (user preferences, prior decisions)
- Quick lookups where you know the exact file path

## Subagent Hygiene

### Context passing
- Pass explicit context (file paths, feature brief content, specific instructions), not "see above"
- Subagents start with **fresh context** — they cannot see your conversation history
- Exception: agents with "access to current context" can see prior messages, but don't rely on this for critical info

### Prompt design
- Keep subagent prompts under 500 words — longer prompts hit instruction-following limits
- Be specific about what output format you expect
- Include acceptance criteria: "Your output should include X, Y, Z"

### Agent type selection
- `subagent_type: "general-purpose"` — for tasks needing Write/Edit access (test writing, code review with file output)
- `subagent_type: "Explore"` — for read-only research and codebase exploration (faster, no write access)
- `subagent_type: "Bash"` — for running commands, git operations, build/test execution
- `subagent_type: "Plan"` — for designing implementation approaches (read-only, returns a plan)

### Parallelism
- Launch independent subagents in parallel using multiple Task tool calls in one message
- Do NOT duplicate work between subagents — if one is researching topic A, don't also research topic A yourself
- Use `run_in_background: true` for long tasks you don't need immediately
