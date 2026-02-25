# AI-Assisted UI Development Workflows: Research Report

**Date:** 2026-02-25
**Scope:** Best practices and emerging workflows for AI-assisted, UI-driven development processes

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design-First vs Code-First: How AI Changes the Calculus](#design-first-vs-code-first)
3. [Figma-to-Code Workflows: State of the Art](#figma-to-code-state-of-the-art)
4. [Iterative Design-Code Feedback Loops](#iterative-design-code-loops)
5. [Design System Automation](#design-system-automation)
6. [Prototyping with AI](#prototyping-with-ai)
7. [Multi-Agent UI Workflows](#multi-agent-ui-workflows)
8. [Process Frameworks for AI-Assisted UI Development](#process-frameworks)
9. [Industry Case Studies](#industry-case-studies)
10. [Actionable Recommendations](#actionable-recommendations)

---

## 1. Executive Summary

The AI-assisted UI development landscape has undergone a fundamental transformation between 2025 and early 2026. Three converging trends define the current state:

1. **Bidirectional design-code bridges** have matured. Figma's MCP server (June 2025) and Claude Code-to-Figma integration (February 2026) close the loop between design tools and code editors, enabling true round-trip workflows.

2. **Spec-driven development (SDD)** has emerged as the disciplined counterweight to "vibe coding." Tools like Kiro (Amazon, July 2025), GitHub Spec Kit (September 2025), and established workflows in Claude Code enforce a requirements-first approach that produces maintainable, production-quality code.

3. **Design tokens have a stable standard.** The W3C Design Tokens Community Group published its first stable specification (2025.10) in October 2025, enabling vendor-neutral token interchange and AI-powered design system automation.

The central finding: **the winning workflow is not "design-first" or "code-first" but "spec-first."** AI collapses the time between specification, design, and implementation to minutes instead of days, but only when guided by explicit requirements, design tokens, and automated quality gates.

---

## 2. Design-First vs Code-First: How AI Changes the Calculus

### The Traditional Dichotomy

| Approach | Strengths | Weaknesses |
|----------|-----------|------------|
| **Design-first** (Figma/Sketch then handoff) | Visual exploration, stakeholder alignment, pixel control | Slow iteration, design drift, lossy handoff |
| **Code-first** (prototype in code) | Immediate interactivity, real constraints, no translation loss | Harder for non-developers to participate, less visual exploration |

### How AI Dissolves the Boundary

AI tools have collapsed the gap between these approaches:

- **Design-to-code is near-instant.** Builder.io's Visual Copilot generates production React from Figma designs in seconds. Figma's MCP server lets Claude Code pull design data (components, variables, layout structure) directly into the IDE.
- **Code-to-design is now possible.** Claude Code-to-Figma (February 2026) captures production UI and converts it into editable Figma frames. This was previously a one-way street.
- **Natural language bridges both.** v0 (Vercel), Bolt, and Lovable accept text descriptions and produce working UI, making "design" accessible through language.

### The New Decision Framework

The question is no longer "design first or code first?" but rather "what fidelity do I need at what stage?"

| Situation | Recommended Starting Point | Why |
|-----------|---------------------------|-----|
| Exploring novel interaction patterns | Design tool (Figma) | Visual exploration + stakeholder communication |
| Implementing from an existing design system | Code (with AI + design tokens) | Tokens constrain the design space; code is faster |
| Rapid prototyping / validation | AI text-to-UI (v0, Bolt, Lovable) | Fastest path to interactive prototype |
| Iterating on production UI | Bidirectional loop (Claude Code + Figma MCP) | Edit in whichever tool is most efficient, sync both ways |
| New component for design system | Figma (design) then Code Connect (mapping) | Need both the visual component and the code implementation |

### Key Insight

The highest-leverage workflow starts with a **specification** (not a mockup and not code). AI tools can generate both mockups and code from specs, but generating good specs from code or mockups is harder. Addy Osmani's workflow (Google Chrome team lead) emphasizes starting with "brainstorming a detailed specification with the AI, then outlining a step-by-step plan before writing actual code."

---

## 3. Figma-to-Code Workflows: State of the Art

### 3.1 The Figma MCP Server

Released June 2025, the Figma MCP server is a middleware layer that exposes design data to AI coding agents. It supports two server types:

- **Desktop MCP server**: Runs locally through the Figma desktop app
- **Remote MCP server**: Connects directly to Figma's hosted endpoint

Key capabilities:
- Select a Figma frame and turn it into code (Claude Code, Cursor, or any MCP-compatible IDE)
- Pull variables, components, and layout data into the IDE
- Automatic design system rule generation: scans the codebase and outputs structured rules (token definitions, component libraries, style hierarchies, naming conventions)

**Practical setup (Claude Code):**
```bash
# Enable in Figma Desktop: Preferences > Enable Dev Mode MCP Server
claude mcp add --transport sse figma-dev-mode-mcp-server http://127.0.0.1:3845/sse
```

### 3.2 Figma Code Connect

Code Connect links Figma design components to actual code components in the codebase. Two approaches:

- **Code Connect UI** (in-browser): Connects Figma to GitHub repos, uses AI to suggest correct code files for mapping. No local setup needed.
- **Code Connect CLI** (local): Runs in the repo, supports property mappings and dynamic code examples for deeper integration.

Supported frameworks: React, React Native, Storybook, HTML (Web Components, Angular, Vue), SwiftUI, Jetpack Compose.

When Code Connect is configured, Figma Dev Mode shows **real production code snippets** instead of autogenerated examples. The MCP server enhances this further by surfacing Code Connect data to AI agents during code generation.

### 3.3 Design Tokens Pipeline

The pipeline has standardized significantly:

```
Figma Variables
    |
    v
Tokens Studio Plugin (exports to JSON)
    |
    v
W3C DTCG Format (.tokens.json)
    |
    v
Style Dictionary v4 (transforms)
    |
    v
Platform outputs (CSS, Tailwind config, Swift, Kotlin)
```

**W3C Design Tokens Specification (2025.10):** First stable version published October 2025. Uses `$value`, `$type`, `$description` format. Supported by 10+ tools including Figma, Penpot, Sketch, Framer, Supernova, zeroheight.

**Style Dictionary v4:** First-class DTCG support. Converts between legacy and DTCG formats. Transforms tokens into any platform output.

**Practical example (from SmallStep Engineering):** Tokens Studio exports from Figma to GitHub-synced JSON files. Style Dictionary transforms these into a custom Tailwind config. Token updates in Figma automatically propagate to every component and project using the UI package.

### 3.4 Builder.io Visual Copilot

A specialized Figma-to-code AI trained on 2M+ data points:
- Generates React, Vue, Svelte, Angular, Qwik, Solid, or HTML
- Supports Tailwind, Emotion, Styled Components, plain CSS
- Claims pixel-perfect accuracy with automatic responsive adjustments
- Can map Figma components to existing code components in your design system

**Key limitation:** Best results require well-structured Figma files (auto layout, named layers, design tokens applied to variables).

### 3.5 Claude Code-to-Figma (Code to Canvas)

Announced February 2026. Enables the reverse direction:
- Capture production UI from browser (production, staging, localhost)
- Convert to fully editable Figma frames
- Edit in Figma, then pull changes back to code

This completes the **bidirectional loop**: Design in Figma > generate code with Claude > capture working UI back to Figma > refine on canvas > push updates back to code.

**Reported impact:** Design-to-code translation time dropped from ~8-10 hours/week to ~2-3 hours/week.

---

## 4. Iterative Design-Code Feedback Loops

### 4.1 The New Feedback Cycle

The traditional design-development feedback loop (design > handoff > implement > review > redesign) took days or weeks per cycle. AI compresses this to minutes:

```
Spec/Prompt
    |
    v
AI generates UI code (minutes)
    |
    v
Visual review in browser (immediate)
    |
    v
Refine via prompt or edit (minutes)
    |
    v
Capture to Figma if needed (seconds)
    |
    v
Stakeholder review in Figma (async)
    |
    v
Pull updates back to code (minutes)
```

### 4.2 The AI Feedback Loop in Design Systems

A notable circularity has emerged: AI learns from design systems, generates new designs based on those patterns, and those AI-generated designs feed back into the next iteration of the system. This can be either virtuous (systems converge on consistency) or dangerous (systems calcify around AI biases).

**Mitigation:** Human review at each cycle, explicit design principles documented as constraints, and periodic "creative divergence" exercises outside AI tooling.

### 4.3 The "Ralph Wiggum" Autonomous Loop Pattern

An emerging pattern runs AI agents in autonomous loops until predefined completion criteria are met. The agent repeatedly attempts implementation, checks against tests or visual criteria, and iterates until convergence. This works best for:
- Component variants (generate all responsive breakpoints)
- Accessibility compliance (iterate until axe-core passes)
- Visual regression (iterate until screenshot diff is below threshold)

### 4.4 Practical Tightening Strategies

1. **Hot-reload + AI:** Run the app with hot reload. Describe changes to the AI. See results immediately. Iterate.
2. **Screenshot-driven refinement:** Screenshot the current state, paste into the AI with "make X change," get updated code.
3. **Figma bidirectional sync:** For stakeholder-facing changes, push code to Figma, get feedback in Figma comments, pull changes back.
4. **Test-driven visual development:** Write visual regression tests first, then prompt the AI to implement until tests pass.

---

## 5. Design System Automation

### 5.1 AI-Powered Token Management

AI automates multiple aspects of design token workflows:
- **Extraction:** ML models scan existing designs to identify color palettes, typography scales, spacing patterns
- **Naming:** AI proposes semantic token names following team conventions
- **Synchronization:** MCP-based tools detect token changes and propagate updates across design system and connected code repos
- **Auditing:** AI flags inconsistencies between token definitions and actual usage

**Reported impact:** Organizations using AI in design systems report 62% reduction in design inconsistencies and 78% improvement in workflow efficiency (2025 peer-reviewed study).

### 5.2 Component Generation and Maintenance

Current capabilities:
- **Text-to-component:** Describe a component, get production code that follows your design system
- **Variant generation:** AI creates responsive variants, dark mode versions, RTL layouts
- **Documentation:** AI drafts component documentation and updates it when code changes
- **Compliance checking:** Real-time validation against style guides via MCP

**Key tools:**
- **Figma MCP Server:** Scans codebase and outputs structured design system rules
- **Motiff:** Real-time component validation and style guide checking
- **Creatie:** Automated layout generation and documentation templates
- **Supernova.io:** AI-powered design system documentation and code export

### 5.3 The MCP-Enabled Design System Workflow

MCP (Model Context Protocol) has become the critical enabler for design system automation. The workflow:

1. **Design system rules file:** Figma MCP server scans codebase, generates rules file documenting token definitions, component libraries, style hierarchies
2. **AI-assisted development:** When generating new components, the AI references the rules file to ensure consistency
3. **Automated enforcement:** CI/CD validates generated code against design system rules
4. **Bidirectional sync:** Changes in code propagate to Figma, changes in Figma propagate to code

### 5.4 Projection

By 2026, 80% of organizations are projected to have generative AI in production. Design systems are evolving from "static libraries" to "living, generative engines" — built for AI consumption, not just human consumption.

---

## 6. Prototyping with AI

### 6.1 The Three Frontrunners

| Tool | Best For | Revenue Traction | Key Differentiator |
|------|----------|------------------|--------------------|
| **v0 (Vercel)** | Frontend component prototyping | N/A (part of Vercel) | Best React/Next.js output; Figma upload support; Vercel deployment |
| **Bolt (StackBlitz)** | Full-stack app prototyping | $40M ARR in 4.5 months | Runs entirely in browser via WebContainer; frontend + backend + database |
| **Lovable** | Non-technical user app building | $17M ARR in 3 months | Full-stack from natural language; auth, DB, deployment included |

### 6.2 Prototyping Workflow Patterns

**Pattern 1: Throwaway Prototype (Validation)**
```
Idea > v0/Bolt/Lovable prompt > Interactive prototype > User testing > Discard prototype > Build production version
```
Use when: Validating interaction patterns, testing user flows, stakeholder alignment.

**Pattern 2: Prototype-to-Production (Evolution)**
```
Idea > v0 prompt > Refine in v0 > Export to Next.js > Refine in IDE with AI > Production
```
Use when: Simple UI, well-understood patterns, time pressure.

**Pattern 3: Design-Informed Prototype**
```
Figma design > Screenshot/URL to v0 > Generated code > Refine > Export
```
Use when: Design exists but manual coding feels wasteful.

### 6.3 The Gap Between Prototype and Production

All three platforms have improved significantly, but the gap remains significant for:
- Complex state management
- Authentication and authorization flows
- Performance optimization
- Accessibility compliance
- Design system integration
- Testing and error handling

**Best practice:** Use AI prototyping for validation and stakeholder alignment. Build production versions with proper engineering discipline (specs, tests, code review).

### 6.4 AI Prototyping for Product Managers

Lenny Rachitsky's guide recommends product managers use AI prototyping to validate concepts before involving engineering. This flips the traditional flow:

**Old:** PM writes PRD > Engineer builds prototype > User tests > Iterate
**New:** PM prompts AI prototype > User tests > PM refines prototype > Engineer builds production version (informed by working prototype)

---

## 7. Multi-Agent UI Workflows

### 7.1 Current State of Multi-Agent Development

Multi-agent workflows are emerging but orchestration is still largely manual. The typical pattern involves specialized agents for distinct phases:

1. **Design Agent:** Generates or interprets designs (Figma MCP, v0)
2. **Code Agent:** Implements components (Claude Code, Cursor, GitHub Copilot)
3. **Test Agent:** Generates and runs tests (Codium, QA Wolf)
4. **Review Agent:** Validates code quality and consistency (independent review subagent)
5. **Documentation Agent:** Updates docs alongside code changes

### 7.2 Practical Multi-Agent Patterns

**Sequential Pipeline:**
```
Design interpretation > Code generation > Test generation > Review > Documentation
```
Each agent hands off to the next. Simple to reason about, but slow.

**Parallel with Merge:**
```
Design interpretation ──> Code generation ──> Integration
                     └──> Test generation ──┘
```
Code and tests generated in parallel, then validated together. Faster, requires shared spec.

**Supervisory Pattern:**
```
Orchestrator agent
    ├── Design agent
    ├── Code agent
    ├── Test agent
    └── Review agent
```
One agent coordinates others. Most flexible but requires sophisticated orchestration.

### 7.3 Emerging Orchestration Tools

- **Claude Code:** Terminal-based agent with subagent capabilities (Task tool for isolated contexts)
- **Roo Code:** VS Code extension with task-specific modes
- **CrewAI:** Role-based multi-agent framework for team-like collaboration
- **Warp:** Terminal with parallel agent execution
- **MCP + Agent2Agent protocols:** Emerging standards for cross-agent communication

### 7.4 The Storacha-Relevant Parallel

The existing Storacha `aidev` workflow already implements a multi-agent pattern:
- **Phase 3 test writer** (isolated subagent) writes acceptance tests
- **Phase 4 implementer** (main agent) builds code
- **Review subagent** performs independent code review
- **Phase 5 feedback loop** uses three specialized agents (validator, executor, reviewer)

This is one of the more sophisticated multi-agent workflows in practice today. For UI work, the pattern could extend to include a design interpretation agent at Phase 2.

---

## 8. Process Frameworks for AI-Assisted UI Development

### 8.1 Spec-Driven Development (SDD)

SDD has emerged as the dominant methodology for disciplined AI-assisted development. Three major implementations:

**GitHub Spec Kit** (open source, September 2025):
```
Constitution > Specify > Clarify > Plan > Tasks > Implement
```
- Constitution: Project-level constants (tech stack, conventions, constraints)
- Specify: Natural language requirements, user journeys, outcomes
- Plan: Technical blueprint with architecture decisions
- Tasks: Small, independently testable work units
- Implement: Sequential execution with focused review

**Kiro (Amazon, July 2025):**
```
Requirements (EARS notation) > Technical Design > Implementation Tasks > Code
```
- Powered by Claude Sonnet
- Agent hooks: Event-driven automations that fire on file save/create
- MCP integration for external tool access
- Generates user stories with acceptance criteria, technical design with diagrams, and sequenced tasks

**Custom SDD (e.g., Storacha aidev):**
```
Specify > Design > Decompose + Test > Implement > Complete
```
- Phase gates with human approval
- TDD as spec enforcement
- Subagent isolation for independent verification
- Hook-based enforcement of process compliance

### 8.2 The Vibe Coding Methodology (Disciplined Version)

The 2026 "strategic blueprint" for vibe coding emphasizes four disciplined phases:

1. **Comprehensive upfront planning:** Draft technical PRDs, data models, security guardrails before coding
2. **Atomic task breakdown:** "Never ask an AI to build a CRM." Decompose into focused units
3. **Incremental integration and validation:** Integrate one component, test it, review before proceeding
4. **Automated quality gates:** Treat AI code as untrusted code. Apply security scanning, linting, tests automatically

### 8.3 Addy Osmani's LLM Workflow (Practical Individual Framework)

1. **Spec first:** Brainstorm with AI to flesh out requirements. Compile into specification document. ("Waterfall in 15 minutes.")
2. **Task decomposition:** Generate structured task list from plan. Execute sequentially.
3. **Rich context:** Supply relevant code, docs, constraints, patterns. Use tools like `gitingest` to bundle codebase context.
4. **Incremental execution:** One function, one bug, one feature at a time.
5. **Automated validation:** Tests at each step. CI/CD catches issues. Code review (human or AI).
6. **Custom rules:** Project-specific style guides (CLAUDE.md, GEMINI.md) documenting conventions.

### 8.4 The TDD-for-UI Gap

Backend TDD is well-established with AI. UI TDD remains harder because:
- Visual correctness is subjective and hard to assert programmatically
- Component interaction patterns are harder to spec than API contracts
- Accessibility and responsiveness add dimensions that unit tests miss

**Emerging approaches:**
- Visual regression testing (Chromatic, Percy) as the "test" in UI TDD
- Storybook stories as component specs (AI generates code to match stories)
- Accessibility audits (axe-core) as automated acceptance criteria
- Design token compliance as machine-verifiable constraints

### 8.5 Proposed Framework: Spec-Driven UI Development (SDUID)

Synthesizing the best practices from the research, a comprehensive framework for AI-assisted UI development:

```
Phase 1: SPECIFY
  - Define user stories with acceptance criteria
  - Define visual acceptance criteria (reference designs, screenshots, or Figma links)
  - Define design token constraints (colors, typography, spacing)
  - Define accessibility requirements (WCAG level, supported screen readers)

Phase 2: DESIGN
  - Generate initial design in Figma (manual or AI-assisted)
  - OR generate prototype via v0/Bolt/Lovable for validation
  - Establish design tokens (Figma Variables > Tokens Studio > W3C DTCG format)
  - Map components to Code Connect (if design system exists)
  - Export design system rules via Figma MCP

Phase 3: DECOMPOSE + TEST
  - Break into component-level tasks
  - Write visual regression test baselines (Storybook stories + Chromatic)
  - Write accessibility tests (axe-core assertions)
  - Write interaction tests (Testing Library)
  - All tests should fail (red phase)

Phase 4: IMPLEMENT
  - One component at a time, referencing Figma via MCP
  - AI generates code that references design tokens and design system rules
  - Visual regression, accessibility, and interaction tests must pass
  - Tests are frozen (same TDD discipline as backend)

Phase 5: REVIEW + COMPLETE
  - Push code to Figma (Code to Canvas) for designer review
  - Designer reviews in Figma, leaves comments
  - Pull updates back to code
  - Final automated review (subagent)
  - Draft PR with deliverable summary
```

---

## 9. Industry Case Studies

### Vercel (v0 + Next.js)

Vercel's workflow starts with v0 for rapid UI generation, then exports to Next.js projects. The tight integration between v0 (prototyping), Vercel (hosting), and Next.js (framework) creates a cohesive pipeline. Key insight: v0 is positioned as the **starting point** for frontend development, not a replacement for it.

### Figma (MCP + Code Connect + Code to Canvas)

Figma has built the most complete bidirectional design-code bridge:
- **MCP Server** for AI agents to read design data
- **Code Connect** for linking design components to real code
- **Code to Canvas** for pushing code back to Figma
- **Design system rules generation** for AI-consistent code generation

Figma's design systems rewrite (2025) delivered 30-60% faster variable updates and mode switching, indicating investment in making design systems AI-consumable.

### Amazon (Kiro IDE)

Kiro represents the most opinionated spec-driven development environment:
- Requirements in EARS notation (Event, Action, Response, State)
- Automatic technical design generation
- Agent hooks for automated tasks on file events
- Built on VS Code with Claude Sonnet as the AI backend

### GitHub (Spec Kit)

GitHub's open-source approach to SDD provides the framework without the IDE lock-in:
- Works with any AI coding agent (Copilot, Claude Code, Gemini CLI)
- Six-phase workflow with persistent project constitution
- Focus on expanding "safe delegation" from 10-20 minute tasks to multi-hour feature delivery

---

## 10. Actionable Recommendations

### For the Storacha Dashboard (Immediate)

1. **Set up Figma MCP Server integration with Claude Code.** This is the single highest-leverage step for UI development today. The dashboard already uses Next.js + Tailwind, which is the sweet spot for AI code generation.

2. **Establish design tokens early.** Define colors, typography, spacing, and component tokens in Figma Variables. Export via Tokens Studio to W3C DTCG format. Transform with Style Dictionary into Tailwind config. This creates the constraint system that makes AI-generated code consistent.

3. **Use Code Connect** for any reusable components. When the design system has 5+ components, the payoff of Code Connect (real code snippets in Figma Dev Mode, accurate MCP-assisted code generation) exceeds the setup cost.

### For the aidev Workflow (Process Enhancement)

4. **Extend Phase 2 (DESIGN) with visual specification.** Currently, the design phase is read-only codebase exploration. For UI features, add: reference designs (Figma links or screenshots), design token constraints, and accessibility requirements to the feature brief.

5. **Add visual regression testing to Phase 3.** Storybook stories + Chromatic/Percy snapshots serve as visual acceptance tests alongside functional tests. These are machine-verifiable and freeze-able, fitting the existing TDD model.

6. **Add a "design interpretation" subagent** for Phase 2 of UI features. This agent reads Figma designs via MCP, extracts component structure and tokens, and produces a structured design specification that the Phase 3 test writer and Phase 4 implementer can reference.

7. **Support Figma-based review in Phase 5.** Use Code to Canvas to push implementations to Figma for designer review, adding a visual review loop alongside the existing GitHub PR review.

### For AI Prototyping (Strategic)

8. **Use v0 for throwaway prototypes during Phase 1 (SPECIFY).** When exploring UI interactions, a 2-minute v0 prototype is more effective than a paragraph of requirements text. Use it for stakeholder alignment, then discard.

9. **Never ship AI prototypes directly.** The gap between prototype and production remains significant for state management, auth, accessibility, and testing. Always go through the full SDD workflow for production code.

### For Multi-Agent Workflows (Evolutionary)

10. **Formalize the design-code-test agent pipeline.** The current aidev workflow already has multi-agent patterns. For UI work, add explicit agent handoffs:
    - Design interpretation agent (reads Figma, produces structured spec)
    - Test writer agent (writes visual + functional tests from spec)
    - Implementer agent (builds components against tests + design tokens)
    - Visual reviewer agent (compares implementation to design, flags discrepancies)

### For Design System Automation (Medium-Term)

11. **Generate design system rules automatically.** Use Figma MCP's rule generation to produce a structured rules file. Include it in Claude Code context (via CLAUDE.md or MCP) so every AI-generated component follows the system.

12. **Automate token synchronization.** Set up the pipeline: Figma Variables > Tokens Studio > GitHub (JSON) > Style Dictionary > Tailwind config. Changes in Figma automatically propagate to code without manual intervention.

---

## Appendix: Tool Landscape Summary

| Category | Tools | Maturity |
|----------|-------|----------|
| **Design-to-Code** | Figma MCP, Builder.io Visual Copilot, Anima, Locofy.ai | Production-ready |
| **Code-to-Design** | Claude Code to Figma (Code to Canvas) | New (Feb 2026) |
| **AI Prototyping** | v0 (Vercel), Bolt (StackBlitz), Lovable | Production for prototypes |
| **Design Tokens** | W3C DTCG, Tokens Studio, Style Dictionary v4 | Stable standard |
| **Component Mapping** | Figma Code Connect (UI + CLI) | Production-ready |
| **SDD Frameworks** | GitHub Spec Kit, Kiro, Claude Code + aidev | Emerging/mature |
| **Design System Automation** | Figma MCP rules, Supernova, Motiff, Creatie | Emerging |
| **Multi-Agent Orchestration** | Claude Code subagents, CrewAI, Roo Code, Warp | Early/experimental |
| **Visual Testing** | Chromatic, Percy, Playwright visual comparisons | Production-ready |

---

## Sources

- [Addy Osmani - My LLM coding workflow going into 2026](https://addyosmani.com/blog/ai-coding-workflow/)
- [GitHub - Spec-driven development with AI (Spec Kit)](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [GitHub Spec Kit repository](https://github.com/github/spec-kit)
- [Figma Blog - Design Systems And AI: Why MCP Servers Are The Unlock](https://www.figma.com/blog/design-systems-ai-mcp/)
- [Figma Blog - Introducing Claude Code to Figma](https://www.figma.com/blog/introducing-claude-code-to-figma/)
- [Figma Blog - Schema 2025: Design Systems For A New Era](https://www.figma.com/blog/schema-2025-design-systems-recap/)
- [Figma - Code Connect documentation](https://help.figma.com/hc/en-us/articles/23920389749655-Code-Connect)
- [Figma MCP Server guide](https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server)
- [Builder.io - Claude Code + Figma MCP Server](https://www.builder.io/blog/claude-code-figma-mcp-server)
- [Builder.io - Introducing Visual Copilot](https://www.builder.io/blog/figma-to-code-visual-copilot)
- [The New Stack - Beyond vibe coding: the case for spec-driven AI development](https://thenewstack.io/vibe-coding-spec-driven/)
- [InfoQ - Beyond Vibe Coding: Amazon Introduces Kiro](https://www.infoq.com/news/2025/08/aws-kiro-spec-driven-agent/)
- [Kiro IDE](https://kiro.dev/)
- [Keywords Studios - The State of Vibe Coding: A 2026 Strategic Blueprint](https://www.keywordsstudios.com/en/about-us/news-events/news/the-state-of-vibe-coding-a-2026-strategic-blueprint/)
- [Thoughtworks - Spec-driven development: Unpacking 2025's key new AI-assisted engineering practices](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- [W3C Design Tokens Community Group - First stable specification](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/)
- [Style Dictionary - DTCG support](https://styledictionary.com/info/dtcg/)
- [SmallStep - How We Cut UI Development Time in Half with Figma and Token Studio](https://smallstep.com/blog/halving-ui-dev-time-figma-token-studio/)
- [Parallel HQ - Automating Design Systems with AI](https://www.parallelhq.com/blog/automating-design-systems-with-ai)
- [InfoWorld - Multi-agent AI workflows: The next evolution of AI coding](https://www.infoworld.com/article/4035926/multi-agent-ai-workflows-the-next-evolution-of-ai-coding.html)
- [Skywork AI - Figma Dev Mode Review 2025](https://skywork.ai/blog/figma-dev-mode-review-2025/)
- [Anima - Figma to React export guide](https://www.animaapp.com/blog/design-to-code/how-to-export-figma-to-react/)
- [v0 by Vercel](https://v0.app/)
- [Emergent - Best AI Tools for UI Design 2026](https://emergent.sh/learn/best-ai-tools-for-ui-design)
- [Aakash Gupta - Ultimate Guide to AI Prototyping Tools](https://www.news.aakashg.com/p/ai-prototyping-tutorial)
- [Digital Fractal - AI-Driven Prototyping: v0, Bolt, and Lovable Compared](https://digitalfractal.com/ai-driven-prototyping-bolt-lovable-comparison/)
- [GitHub Blog - TypeScript, Python, and the AI feedback loop](https://github.blog/news-insights/octoverse/typescript-python-and-the-ai-feedback-loop-changing-software-development/)
- [AI Design Systems Conference 2026](https://www.intodesignsystems.com)
- [Microsoft Learn - Implement Spec-Driven Development using GitHub Spec Kit](https://learn.microsoft.com/en-us/training/modules/spec-driven-development-github-spec-kit-enterprise-developers/)
