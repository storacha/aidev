# Fullstack UI Development — Claude Code Instructions

## Meta-Rules

1. **Design system first.** Every UI component follows the project's design tokens. Never hardcode colors, spacing, or typography.
2. **Pattern over principle.** Find how the codebase already does it and follow that. Don't invent new component patterns.
3. **Visual before functional.** Get the component looking right (Storybook), then wire it up to data/APIs.
4. **Accessible by default.** Every interactive element needs keyboard navigation, ARIA labels, and contrast compliance.
5. **Test what you see.** Visual regression tests + a11y tests are first-class acceptance criteria, not afterthoughts.

## Workflow Overview

This project uses a 6-phase fullstack development workflow, launched with `/fullstack`:

| Phase | Name | What Happens |
|-------|------|-------------|
| 1 | **specify** | Value questions + visual requirements (Figma links, a11y, breakpoints) |
| 2 | **visual-design** | Design tokens, Figma review, Storybook setup, component architecture |
| 3 | **design** | Technical architecture, API integration, data flow |
| 4 | **decompose** | Task breakdown + acceptance tests (functional + visual + a11y) |
| 5 | **implement** | TDD + visual verification loop |
| 6 | **complete** | Commit, PR, human review |

## Conventions

### File Naming
- Components: PascalCase (`UserProfile.tsx`, `NavBar.tsx`)
- Utilities/hooks: camelCase (`useAuth.ts`, `formatDate.ts`)
- Styles: kebab-case or co-located (`user-profile.css` or `UserProfile.module.css`)
- Tests: `ComponentName.test.tsx` or `ComponentName.spec.tsx`
- Stories: `ComponentName.stories.tsx`

### Component Structure
```
src/
├── components/
│   └── ComponentName/
│       ├── ComponentName.tsx          # Component implementation
│       ├── ComponentName.test.tsx     # Unit/integration tests
│       ├── ComponentName.stories.tsx  # Storybook stories
│       └── index.ts                   # Public export
├── hooks/                             # Custom React hooks
├── lib/                               # Utilities, API clients
├── types/                             # Shared TypeScript types
└── app/                               # Pages/routes (Next.js/React Router)
```

### Imports
- Prefer absolute imports (`@/components/...`, `@/lib/...`)
- Group: React/framework → external packages → internal modules → relative imports
- Use barrel exports (`index.ts`) for component directories

### Styling
- Tailwind CSS as primary styling approach
- Design tokens via CSS custom properties (`var(--color-primary)`)
- No inline `style={}` except for truly dynamic values (calculated positions, animations)
- Responsive: mobile-first (`sm:` → `md:` → `lg:` → `xl:`)

### Error Handling
- Use error boundaries for component-level failures
- API errors: structured error objects, not thrown exceptions in render paths
- Loading states: skeleton components, not spinners (unless very brief operations)
- Empty states: always design the zero-data case

### TypeScript
- Strict mode (`strict: true`)
- Props interfaces: `ComponentNameProps`
- Prefer `interface` for component props, `type` for unions/utilities
- No `any` — use `unknown` and narrow

## Testing Conventions

### Functional Tests
- Framework: Vitest or Jest + React Testing Library
- Test behavior, not implementation (no `querySelector`, no `instance()`)
- Use `screen.getByRole()`, `getByLabelText()`, `getByText()` over `getByTestId()`
- Test user interactions: `userEvent.click()`, `userEvent.type()`

### Visual Regression Tests
- Storybook stories as visual test cases
- Chromatic or Playwright screenshots for regression baselines
- Each component story = one visual test case
- Test states: default, hover, focus, disabled, error, loading, empty

### Accessibility Tests
- Storybook a11y addon (`@storybook/addon-a11y`) for component-level checks
- Axe-core assertions in test files: `expect(await axe(container)).toHaveNoViolations()`
- Keyboard navigation tests: Tab order, Enter/Space activation, Escape dismissal
- WCAG 2.1 AA as minimum target

## Design Generation (No Human Designer)

This workflow has no dedicated designer. The AI generates designs directly in Figma, and the human reviews them in Figma while providing feedback in the Claude Code conversation.

### How It Works

```
1. AI generates design in Figma via generate_figma_design MCP
2. You review it in Figma
3. You tell the AI what to change here in chat
4. AI updates the Figma design
5. Repeat until approved (usually 2-3 rounds)
6. Save approved screenshots as visual reference
7. Proceed to implementation
```

The feedback loop is **conversational** — you look at Figma, you talk to the AI here. No Figma comments needed.

### Agent Figma Account

The AI agent needs its own Figma identity to generate and update designs:

1. Create a Figma account for the agent (e.g., `claude-dev@yourteam.com`)
2. Add it to your Figma team as an **editor** (required for design generation)
3. Generate a Personal Access Token (PAT) from the agent's account settings
4. Set the PAT as environment variable: `export FIGMA_AGENT_PAT=fig_...`

### Design Generation Tools

| Tool | When to Use | How |
|------|------------|-----|
| **Figma MCP** | Default — generates editable Figma frames | `generate_figma_design` from spec or code prototype |
| **Code prototype** | When Figma MCP unavailable, or for rapid iteration | React/Tailwind in `prototypes/{slug}/`, preview in browser |
| **v0.dev** | Highest quality React output | API generates React + shadcn/ui, capture to Figma |
| **Google Stitch MCP** | Alternative design generation | `stitch-mcp` generates designs directly |

## MCP Integrations

### Figma MCP (Design Generation + Token Extraction)
```bash
claude mcp add --transport http figma https://mcp.figma.com/mcp
```
- `generate_figma_design` — generate editable Figma frames from spec or code prototype
- `get_design_context` — structured component/layout data from Figma frames
- `get_variable_defs` — extract design tokens (colors, spacing, typography)
- `get_screenshot` — visual reference for comparison
- `create_design_system_rules` — generate agent rulebook from design system

Requires a dedicated agent Figma account (editor seat) with `FIGMA_AGENT_PAT` set.

### Google Stitch MCP (Design Generation Alternative)
```bash
# Install stitch-mcp for AI design generation
# See: https://github.com/davideast/stitch-mcp
```
- Generates UI designs from text prompts (free during beta)
- 350 standard + 50 experimental generations/month
- Export to Figma via html.to.design plugin

### Storybook MCP (Component Manifest)
```bash
npm install -D @storybook/addon-mcp
```
- `list-all-components` — discover available components and their interfaces
- Component manifest provides token-efficient descriptions of the design system
- Autonomous correction loop: generate → test → fix → human reviews passing code

### Playwright MCP (Visual Verification)
- Take screenshots of generated UI
- Compare against Figma designs (`get_screenshot`)
- Self-correct visual discrepancies before human review

## Design Tokens

### Format
Design tokens follow the W3C Design Tokens Community Group (DTCG) format:
```json
{
  "color": {
    "primary": {
      "$value": "#0066FF",
      "$type": "color",
      "$description": "Primary brand color"
    }
  }
}
```

### Pipeline
```
Figma Variables → Tokens Studio → W3C DTCG JSON → Style Dictionary → Tailwind config + CSS variables
```

### Usage in Code
```tsx
// Tailwind classes (preferred)
<button className="bg-primary text-on-primary">

// CSS custom properties (when Tailwind insufficient)
<div style={{ color: 'var(--color-primary)' }}>
```

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/fullstack` | Start the 6-phase fullstack development workflow |
| `/review` | Launch independent code review subagent |

## Enforcement Hooks

| Hook | Event | What It Enforces |
|------|-------|-----------------|
| `session-resume.sh` | SessionStart | Re-injects active feature state on startup/resume |
| `workflow-nudge.sh` | UserPromptSubmit | Injects phase context, suggests `/fullstack` |
| `branch-protection.sh` | PreToolUse (Bash) | Blocks git commit/push on main with active feature |
| `pre-commit-checks.sh` | PreToolUse (Bash) | Verifies phase is implement/complete before commits |
| `phase-gate.sh` | PreToolUse (Edit/Write) | Blocks files that don't match current phase |
| `tdd-guard.sh` | PreToolUse (Edit/Write) | Requires test snapshot before source files |
| `test-mod-detector.sh` | PreToolUse (Edit/Write) | Flags acceptance test modifications |
| `review-gate.sh` | PreToolUse (Edit/Write) | Blocks phase transitions without required artifacts |
| `process-guard.sh` | PreToolUse (Edit/Write) | Protects process files from unauthorized modification |
| `stop-decompose-verify.sh` | Stop | Verifies tests fail (RED) during decompose phase |
