# When to Use Subagents

## Always use a subagent for:
- **Phase 4 acceptance test writing** — context isolation prevents implementation knowledge from leaking into tests
- **Phase 5 code review** (reviewer pattern from `/review` skill) — independent verification in fresh context
- **Figma design interpretation** — isolate visual analysis from code generation
- **Research tasks** — web search, spec lookup, broad exploration

## Consider a subagent for:
- Exploring an unfamiliar codebase
- Investigating complex visual bugs (isolate investigation from fix attempts)
- Long-running searches that might return large results
- Component library audit (inventory existing components via Storybook MCP)

## Do NOT use a subagent for:
- Simple file reads or searches (use Grep/Glob directly)
- Single-file edits with clear instructions
- Tasks requiring main conversation context (user preferences, prior decisions)
- Quick lookups where you know the exact file path

## Subagent Hygiene

### Context passing
- Pass explicit context (file paths, brief content, specific instructions), not "see above"
- Subagents start with fresh context — they cannot see your conversation history
- Exception: agents with "access to current context" exist but don't rely on this for critical info

### Prompt design
- Keep prompts under 500 words
- Be specific about expected output format
- Include acceptance criteria: "Your output should include X, Y, Z"

### Agent type selection
- `subagent_type: "general-purpose"` — tasks needing Write/Edit (test writing, code review with output)
- `subagent_type: "Explore"` — read-only research and codebase exploration (faster)
- `subagent_type: "Bash"` — running commands, git operations, build/test execution
- `subagent_type: "Plan"` — designing implementation approaches (read-only)

### Parallelism
- Launch independent subagents in parallel using multiple Task tool calls in one message
- Do NOT duplicate work between subagents
- Use `run_in_background: true` for long tasks you don't need immediately
