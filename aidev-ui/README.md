# aidev-ui — AI Development Tooling for Fullstack UI Projects

Structured AI development workflow for projects with UI + backend. Parallel to `aidev/` (backend-only process) but fully independent.

## Quick Start

```bash
# From your UI project root:
./aidev-ui/setup.sh

# Start Claude Code:
claude

# Begin a feature:
/fullstack <description>
```

## What This Provides

- **6-phase workflow**: specify → visual-design → design → decompose → implement → complete
- **Visual-design phase**: Figma MCP integration, design token extraction, Storybook setup
- **Visual regression testing**: Storybook stories + Chromatic baselines as acceptance tests
- **Accessibility gates**: a11y tests are first-class acceptance criteria
- **TDD enforcement**: same test-first discipline as aidev, extended for visual testing
- **Hook enforcement**: 10 hooks prevent phase violations, protect process files

## How It Differs from aidev/

| Aspect | aidev (Backend) | aidev-ui (Fullstack) |
|--------|----------------|---------------------|
| Skill | `/dev` | `/fullstack` |
| Phases | 5 (specify → design → decompose → implement → complete) | 6 (adds visual-design between specify and design) |
| Test types | Unit/integration | Unit/integration + visual regression + a11y |
| MCP tools | None required | Figma MCP + Storybook MCP + Playwright MCP |
| Conventions | Go + JS, UCAN capabilities | React/TypeScript/Tailwind, design tokens |
| Process proposals | `AIPIP/` | `aipip-ui/` |

## MCP Setup (One-Time)

```bash
# Figma — reads designs, tokens, components
claude mcp add --transport http figma https://mcp.figma.com/mcp

# Storybook — component manifest for AI reuse
npm install -D @storybook/addon-mcp

# Playwright — visual verification screenshots
npx playwright install
```

## Agent Figma Account Setup

The AI agent needs its own Figma identity to generate designs:

1. **Create a Figma account** for the agent (e.g., `claude-dev@yourteam.com`)
2. **Add to your Figma team** as an **editor** (required — the agent generates designs)
3. **Generate a PAT** from the agent's account: Figma Settings → Personal Access Tokens
4. **Set the environment variable:**
   ```bash
   export FIGMA_AGENT_PAT=fig_...
   ```
5. **Invite to relevant Figma projects** so the agent can read/write files

The agent generates designs in Figma. You review them in Figma and give feedback directly in the Claude Code conversation — no Figma comments needed.

## Directory Structure

```
aidev-ui/
├── aipip-ui/          # Process improvement proposals
├── .claude/
│   ├── hooks/         # 10 enforcement hooks
│   ├── rules/         # Workflow rules and conventions
│   ├── skills/        # /fullstack, /review, /setup
│   └── settings.json  # Hook wiring
├── .specs/
│   ├── active/        # In-progress features
│   ├── done/          # Completed features
│   └── TEMPLATE-*.md  # Spec templates
├── CLAUDE.md          # Project instructions (symlinked to project root)
├── setup.sh           # Creates symlinks
└── README.md          # This file
```

## Cannot Coexist with aidev/ in Same Project

Both processes create `.claude` and `CLAUDE.md` symlinks. A project uses one OR the other:
- Backend service → `aidev/`
- Fullstack UI project → `aidev-ui/`
