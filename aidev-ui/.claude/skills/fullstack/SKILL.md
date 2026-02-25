---
name: fullstack
description: "Start the fullstack UI development workflow: specify, visual-design, design, decompose, implement, complete"
user_invocable: true
---

# Fullstack UI Development Workflow

This skill orchestrates the full Specify -> Visual-Design -> Design -> Decompose -> Implement -> Complete workflow for fullstack UI features. It handles design token integration, Storybook-driven component development, visual regression testing, and accessibility validation alongside standard TDD.

## Entry Point

When invoked, you receive the user's feature request as `$ARGUMENTS`. Your first job is to check for unfinished work, then classify the complexity tier.

## Step 0: Unfinished Work Check

Before starting any new feature, check for existing in-progress work:

1. **Check `.specs/active/` for active specs.** If any feature directory exists (not just `.gitkeep`):
   - Read the `PHASE` file to determine current phase
   - If phase is `implement` or earlier: "You have unfinished work on `{feature}` (phase: `{phase}`). Resume this feature, or archive it first?"
   - If phase is `complete`: "Feature `{feature}` has a draft PR awaiting review. Check the PR for feedback before starting new work."
   - Do NOT proceed to a new feature until the user explicitly says to archive or continue.

2. **Check for open draft PRs with pending feedback.** Run `gh pr list --draft --author @me` in the target repo.

## Step 1: Tier Detection

Analyze the request and classify:

### Tier 0: Trivial (Just Do It)
- Style tweak, copy change, single component fix
- Touches 1-2 files max, no new components, no design changes
- **Action:** Implement directly, show diff. No spec needed.
- **But first:** Tier 0 Sanity Check (below).

### Tier 1: Quick (2-3 min planning)
- Bug fix with known cause, small scoped UI change
- Touches 2-5 files, single component change or minor layout adjustment
- **Action:** Quick brief -> Skip Visual-Design and Design -> Decompose -> Implement

### Tier 2: Standard (5-10 min planning)
- New component, new page, significant UI enhancement
- Touches 5-15 files, multiple related components or a full feature slice
- **Action:** Full brief -> Visual-Design -> Design -> Decompose -> Implement

### Tier 3: Full (15-25 min planning)
- New section/module, design system changes, major UX overhaul
- Touches 10+ files across multiple directories
- **Action:** Full brief -> Visual-Design -> Full Design Doc -> Decompose -> Implement

**Present your tier assessment:**
> "This looks like a **Tier [N]** ([label]) change because [reason]. I'll [describe the process]. Sound right?"

### Tier 0 Sanity Check
Escalate to Tier 1 if the change:
- Touches more than 3 files
- Modifies shared components used by 3+ other components
- Changes design tokens or theme configuration
- Touches test infrastructure or CI config
- Adds new dependencies

## Step 2: PHASE 1 — SPECIFY (Value + Visual Requirements)

### Create the spec directory
```
echo "specify" into .specs/active/{feature-slug}/PHASE
```

### Ask value questions

**All tiers (Tier 1+):**
1. **What problem does this solve?** (What's broken/missing, and for whom?)
2. **Who benefits?** (End users? Internal team? Both?)
3. **What does success look like?** (Measurable outcome)
4. **What's the time appetite?**

**Tier 2+ additional questions:**
5. **What's the simplest version?**
6. **What should we NOT build?**
7. **Known rabbit holes or risks?**

**UI-specific questions (Tier 2+):**
8. **Figma link?** (If a design exists, get the URL.)
9. **Responsive requirements?** (Which breakpoints? Mobile-first?)
10. **Accessibility requirements?** (Beyond WCAG 2.1 AA baseline?)
11. **Animation/interaction expectations?** (Static, transitions, rich animations?)
12. **Existing components to reuse?** (Search codebase for patterns.)

**Smart questioning rules:**
- Skip questions you can answer from context.
- For question 12, proactively search the codebase. Use Grep/Glob to find similar components, then present what you found.
- Be conversational, not form-filling.

### Produce the Feature Brief
Create `.specs/active/{feature-slug}/brief.md` using the template at `.specs/TEMPLATE-feature-brief.md`.

Acceptance criteria MUST include:
- **Functional:** behavior on interaction
- **Visual:** layout matches design, responsive breakpoints work
- **Accessibility:** keyboard navigable, screen reader correct, contrast passes

### Review Gate (MANDATORY)
> "Here's the feature brief. Please review the acceptance criteria — these become the tests. Approve before I move to visual design?"

After approval:
- **Tier 1:** Update phase to `decompose` (skip visual-design and design).
- **Tier 2+:** Update phase to `visual-design`.

## Step 3: PHASE 2 — VISUAL-DESIGN (AI Generates, Human Reviews)

**Constraint: No production source code. Prototype code + design config files (JSON tokens, CSS) ARE allowed.**

In this workflow there is no human designer. The AI generates visual designs and the human reviews them in Figma or the browser, providing feedback until approved.

### 3a. Design Generation

Choose the path based on what's available:

**Path A: Figma-First (Recommended)**
Generate designs directly in Figma. The user reviews in Figma and gives feedback in the conversation.

1. **Generate a Figma design** from the spec using Figma MCP `generate_figma_design`. Include layout, typography, colors, spacing from existing design tokens.
2. **Present to user:**
   > "I've generated a design in Figma. Please review it and let me know what you'd like changed — just describe it here."
3. **Iterate:** User describes changes in chat, AI updates the Figma design via MCP. Repeat until approved. Typical: 2-3 rounds.

**Path A fallback: Code prototype + Figma capture**
If `generate_figma_design` is unavailable or too limited:
1. Generate a React/HTML prototype in `prototypes/{feature-slug}/`
2. Preview in browser (dev server)
3. Capture to Figma via `html.to.design` plugin (user pastes preview URL)
4. User reviews in Figma, gives feedback in chat
5. AI updates prototype, recaptures. Repeat until approved.

**Path B: Existing Figma Design Provided**
If the user provides a Figma link:
1. Use Figma MCP `get_design_context` to extract component structure
2. Use `get_variable_defs` to extract design tokens (colors, spacing, typography)
3. Use `get_screenshot` to capture visual reference
4. Document the design interpretation in brief.md

**Path C: Google Stitch (Free Alternative)**
If Stitch MCP is configured:
1. Craft a prompt from the feature spec
2. Use Stitch MCP to generate the design
3. Export to Figma (via Stitch's "Copy to Figma" or html.to.design plugin)
4. User reviews in Figma

**Path D: v0.dev (Highest Code Quality)**
If v0 is available:
1. Use v0 API to generate React/Tailwind prototype from spec
2. Preview the v0 output
3. Export to Figma via html.to.design if Figma review is needed
4. Use the v0 output as the implementation starting point (not throwaway)

### 3b. Design Token Review
1. Check for existing tokens (`tokens.json`, CSS custom properties, Tailwind config)
2. If tokens exist: verify the prototype uses them. Flag any gaps.
3. If tokens don't exist: extract a minimal token set from the approved prototype (colors, spacing scale, typography scale)
4. Document under `## Design Tokens` in brief.md

### 3c. Component Architecture
Map out component hierarchy based on the approved prototype:
```
FeatureName/
├── FeatureContainer.tsx    # State, data fetching
├── FeatureView.tsx         # Layout, passes props
├── SubComponentA.tsx       # Reusable piece
└── SubComponentB.tsx       # Reusable piece
```

Identify: new vs existing components, props interfaces, state management approach.

### 3d. Storybook Planning
List stories per new component: default, variants, edge cases, interactive states.

### 3e. Clean Up Prototype
After the visual design is approved:
- If using Path A: delete the throwaway prototype (`prototypes/{feature-slug}/`)
- If using Path D (v0): keep the v0 output as the implementation starting point
- Save approved Figma screenshots to `.specs/active/{feature-slug}/visual-reference/` for implementation reference

### Review Gate (MANDATORY)
> "Here's the visual design (approved in Figma), component architecture, tokens, and Storybook plan. Approve before I do technical design?"

After approval, update phase to `design`.

## Step 4: PHASE 3 — DESIGN (Technical Architecture)

**Constraint: Markdown only.**

### Design Activities
1. Read brief and visual-design notes
2. Explore codebase: find files to change, data flow, test patterns
3. Identify risks and dependencies

### Produce Design Notes
**Tier 2:** `## Design Notes` section in `brief.md` — files, APIs, state, test strategy.
**Tier 3:** Separate `design.md` with architecture diagram, migration plan.

### Review Gate (MANDATORY)
> "Here's the technical design. I've identified [N] files to change. Approve before I write tests?"

After approval, update phase to `decompose`.

## Step 5: PHASE 4 — DECOMPOSE + ACCEPTANCE TESTS

**Constraint: Only test files and Storybook stories. No source files.**

### 5a. Task Decomposition
Write to `.specs/active/{feature-slug}/tasks.md`.

Typical UI task ordering:
1. Design tokens / theme setup
2. Base components (atoms)
3. Composite components (molecules)
4. Feature components (organisms)
5. Page integration (routes, data fetching)
6. Responsive / accessibility polish

### 5b. Write Acceptance Tests (via subagent)

**CRITICAL: Use a subagent (Task tool) for test writing.**

Subagent receives: feature brief, acceptance criteria, test patterns, component architecture.
Subagent does NOT receive: implementation details, source code snippets, design reasoning.

Three test types:
- **Functional tests** (Testing Library): interactions, API calls, state changes
- **Storybook stories** (visual regression): one story per state, all variants, edge cases
- **Accessibility assertions**: axe-core, keyboard nav, ARIA checks

### 5c. Create Test Snapshot
Copy test files to `.specs/active/{feature-slug}/tests-snapshot/`.

### 5d. Write Subagent Attestation
```json
{
  "written_by": "subagent",
  "timestamp": "ISO8601",
  "test_files": ["list of test file paths"],
  "brief_hash": "first 8 chars of sha256(brief.md)"
}
```

### 5e. Verify Tests Fail (RED)

### Review Gate (MANDATORY)
> "Here are the acceptance tests (all failing/RED). Approve before I implement?"

After approval, update phase to `implement`.

## Step 6: PHASE 5 — IMPLEMENT (TDD + Visual Verification)

### Context Refresh
Re-read brief.md, tasks.md, all test files.

### For Each Task (in dependency order)

1. **Check dependencies.** Verify predecessors complete.
2. **Write CURRENT_TASK file:** `echo "N" into .specs/active/{feature-slug}/CURRENT_TASK`
3. **Read acceptance test.** Quote the criterion.
4. **Write unit tests.** (RED)
5. **Implement minimal code.** (GREEN) — component-first, verify stories render.
6. **Visual verification loop** (with Playwright MCP): screenshot → compare → self-correct.
7. **Refactor.** (REFACTOR)
8. **Self-audit:** functional + visual + a11y criteria.
9. **Run full test suite + lint + type-check.**
10. **Mark task complete.**

### After ALL Tasks — Mandatory Code Review
Launch `/review --final {feature-slug}`. Subagent writes `reviews/final.json`.

### Test Freeze
Acceptance tests frozen. If wrong: STOP, use `/review` with evidence.

### Stop-and-Redecompose Triggers
- Task requires more files than planned
- Undocumented dependency
- Design tokens insufficient
- Component architecture doesn't work
- 3+ approaches for same failure

## Step 7: PHASE 6 — COMPLETE

1. Run full test suite
2. Final self-audit
3. Commit to `feat/{feature-slug}`
4. Push + draft PR (`gh pr create --draft`)
5. Present PR link + deliverable summary
6. Human review + feedback loop (fixup commits, never force-push)
7. After merge: move to `.specs/done/`

## Phase File Reference

`.specs/active/{feature-slug}/PHASE` values:
- `specify` — Phase 1
- `visual-design` — Phase 2
- `design` — Phase 3
- `decompose` — Phase 4
- `implement` — Phase 5
- `complete` — Phase 6
- `done` — Merged

## Quick Reference: What Each Phase Produces

| Phase | Produces | Allowed File Types |
|-------|----------|--------------------|
| 1. Specify | `brief.md` with visual requirements | Markdown only |
| 2. Visual-Design | Token notes, component architecture, story plan | Markdown + design config |
| 3. Design | Design notes / `design.md` | Markdown only |
| 4. Decompose | `tasks.md` + tests + stories + snapshot + attestation | Test + story files only |
| 5. Implement | Source + unit tests + `reviews/final.json` | All except acceptance tests |
| 6. Complete | Feature branch + draft PR | No new files |
