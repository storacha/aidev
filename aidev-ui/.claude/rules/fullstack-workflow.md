# Fullstack Development Workflow Rules

## Phase Ordering (Mandatory)
You MUST follow this sequence. NEVER skip a phase (except Tier 1 shortcuts).
1. SPECIFY: Value questions + visual requirements. No code, no design.
2. VISUAL-DESIGN: Figma review, design tokens, component architecture, Storybook planning. Design config files allowed.
3. DESIGN: Technical architecture, API integration. Markdown only.
4. DECOMPOSE + TEST: Tasks + acceptance tests (functional + visual + a11y). Tests MUST fail.
5. IMPLEMENT: TDD + visual verification loop. Tests are FROZEN.
6. COMPLETE: Commit, push, draft PR. Human reviews on GitHub.

## Phase Constraints
- Phase 1: PLAN MODE ONLY. No source, test, or config files.
- Phase 2: No source or test files. Design config files (JSON tokens, CSS custom properties) ARE allowed.
- Phase 3: Markdown only. No source, test, or config files.
- Phase 4: ONLY test files and Storybook stories. No source files.
- Phase 5: Source files allowed. Acceptance tests FROZEN. No test modifications.

## Visual-Design Phase Requirements
This phase uses AI-generated designs reviewed by the human. There is no human designer.

**Design Generation Flow:**
1. AI generates design in Figma via `generate_figma_design` MCP (or code prototype as fallback)
2. User reviews in Figma
3. User gives feedback in the Claude Code conversation
4. AI updates the Figma design (or prototype), repeat until approved (typically 2-3 rounds)
5. Approved Figma screenshots saved as visual reference; throwaway prototypes deleted

**Prototype files in `prototypes/` are allowed** during this phase (phase-gate exception).
Production source files are NOT allowed.

Before transitioning from visual-design to design, you MUST have:
- Visual design approved by user (via Figma review or browser preview)
- Component architecture documented (hierarchy, new vs existing)
- Design token decisions documented (using existing tokens, or new ones needed)
- Storybook story plan (which states to cover per component)
- Visual reference screenshots saved to `.specs/active/{feature-slug}/visual-reference/`

## Test Types (Phase 4)
Acceptance tests in fullstack projects include THREE types:
1. **Functional tests** (React Testing Library) — user interactions, API calls, state changes
2. **Storybook stories** — visual regression baselines (one story per component state)
3. **Accessibility assertions** — axe-core violations, keyboard navigation, ARIA attributes

All three types are frozen during Phase 5.

## Visual Verification (Phase 5)
When Playwright MCP is available, use the visual verification loop:
1. Generate/modify component code
2. Take screenshot via Playwright
3. Compare against Figma reference (if available) or Storybook baseline
4. Self-correct visual discrepancies
5. Proceed only when visual output is satisfactory

## Mandatory Review Gates
Use AskUserQuestion to pause at EVERY phase transition:
- After Phase 1: "Feature brief ready. Approve before visual design?"
- After Phase 2: "Visual design plan ready. Approve before technical design?"
- After Phase 3: "Technical design ready. Approve before I write tests?"
- After Phase 4: "Tests ready (all failing). Approve before I implement?"
These gates are mandatory even in high-autonomy mode.

## Tier 0 Sanity Check
Escalate to Tier 1 if the change:
- Touches more than 3 files
- Modifies shared components used by 3+ others
- Changes design tokens or theme configuration
- Touches test infrastructure or CI config
- Adds new dependencies

## Stop-and-Redecompose Triggers
STOP implementation and re-decompose if:
- A task requires changing more than planned files
- You discover an undocumented dependency between tasks
- Design tokens are insufficient (need new tokens not in the plan)
- Component architecture doesn't work as designed
- You've attempted 3+ approaches for the same test failure

## Dependency Enforcement
Tasks use explicit notation:
  - `[ ] Task 3 (after: 1, 2)` — blocked by tasks 1 and 2
  - `[P] Task 4` — independent
Before starting a task, verify ALL predecessors are complete.

## Mandatory Code Review (End of Phase 5)
After ALL tasks are implemented and tests pass, run `/review --final {slug}`.
The review MUST be performed by a subagent — never by the implementing agent.

## Completion Phase (Phase 6)
After tests pass and code review is done:
1. Commit to `feat/{feature-slug}` branch
2. Push and create draft PR (`gh pr create --draft`)
3. Present PR link + deliverable summary
4. Human reviews on GitHub
5. Feedback loop if changes requested (fixup commits, never force-push)
6. After merge: move spec to `.specs/done/`
