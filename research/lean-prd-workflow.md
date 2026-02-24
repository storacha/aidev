# Research Report: Lean AI-Guided PRD/Planning Workflow for Claude Code

## Executive Summary

This report synthesizes research across modern product development methodologies, AI-assisted planning tools, developer productivity research, and value-first thinking frameworks to design a lean, conversational planning workflow for an AI coding assistant. The goal: when a developer says "I want to build X," the AI guides them through **just enough structured thinking** to produce clear, actionable work items -- without it feeling like filling out forms.

The core finding is that the best planning workflows share three properties: **(1)** they force value-first thinking through targeted questions, **(2)** they produce artifacts that are immediately useful for coding, and **(3)** they take minutes, not hours.

---

## Table of Contents

1. [Landscape: How the Best Teams Plan](#1-landscape-how-the-best-teams-plan)
2. [AI-Guided Planning: Current State of the Art](#2-ai-guided-planning-current-state-of-the-art)
3. [Value-First Thinking Frameworks](#3-value-first-thinking-frameworks)
4. [Lean Task Decomposition](#4-lean-task-decomposition)
5. [Anti-Patterns: What Makes Planning a Burden](#5-anti-patterns-what-makes-planning-a-burden)
6. [Research: Planning vs. Productivity](#6-research-planning-vs-productivity)
7. [Recommended Workflow Design](#7-recommended-workflow-design)
8. [Example Question Flows](#8-example-question-flows)
9. [Recommended Templates](#9-recommended-templates)
10. [Must-Have vs. Nice-to-Have](#10-must-have-vs-nice-to-have)
11. [Sources](#11-sources)

---

## 1. Landscape: How the Best Teams Plan

### 1.1 Shape Up (37signals/Basecamp)

Shape Up is the most influential lightweight planning methodology for small product teams. Its core insight: **betting on shaped work is fundamentally different from estimating unshaped work**.

**The Pitch Format** -- five ingredients that force clarity:

| Ingredient | Purpose | Typical Length |
|---|---|---|
| **Problem** | Why does this matter? A specific story showing pain. | 1-3 paragraphs |
| **Appetite** | How much time are we willing to spend? (2 weeks or 6 weeks) | 1 sentence |
| **Solution** | Core elements, shown via breadboards/fat-marker sketches | Visual + 2-5 paragraphs |
| **Rabbit Holes** | Known traps to avoid | Bullet list |
| **No-Gos** | What we explicitly will NOT build | Bullet list |

Key principles relevant to our workflow:
- **Fixed time, variable scope.** The appetite constrains the solution, not the other way around.
- **No tasks upfront.** Teams discover tasks during building, not during planning.
- **Shaped, not specified.** Enough detail to start, not so much that there is no room for judgment.
- Teams of 2 (one designer + one programmer) or 3 at most. Planning overhead scales with team size.

Source: [Shape Up by Ryan Singer](https://basecamp.com/shapeup/1.5-chapter-06), [37signals](https://37signals.com/06)

### 1.2 Linear Method

Linear's philosophy is arguably the most developer-aligned planning approach. Their key provocation: **write issues, not user stories**.

> "User stories are a cargo cult ritual that feels good but wastes a lot of resources and time." -- Linear Method

Their recommendations:
- **Write direct, scannable titles** that immediately convey what needs to be done
- **Keep descriptions minimal** (optional, not required) -- include only relevant context, thoughts, and links
- **Authors should write their own issues** -- this forces deeper problem analysis
- Discuss user experience at the **product and feature level**, not the task level
- Spend time **talking to users and thinking through features** before building, instead of writing user stories

Source: [Write issues, not user stories](https://linear.app/method/write-issues-not-user-stories), [Linear Method](https://linear.app/method)

### 1.3 Vercel's Engineering Culture

Vercel's approach centers on **velocity as the primary metric**, with "Iterate to Greatness" (ITG) as a core value:
- Launch an initial version and rapidly iterate -- not perfection on the first try
- Interns ship PRs to production on their second day
- Reduced PR cycle times from 4.6h to 2.7h (43% reduction) by investing in CI tooling
- Strong pair-programming culture
- Anti-siloed communication -- all context in one place

The key insight: Vercel treats planning as an investment in velocity, not as ceremony. Planning that speeds up shipping is good; planning that slows it down is waste.

Source: [Vercel Engineering Blog](https://vercel.com/blog/improving-developer-workflow), [Vercel DX Case Study](https://getdx.com/customers/vercel/)

### 1.4 GitHub Issues (2025 Evolution)

GitHub has evolved toward lightweight, code-adjacent planning:
- **Sub-issues** (GA in 2025) replace tasklists for hierarchical breakdown
- **Issue types** provide standardized classification (bug, feature, task)
- Everything lives next to the code -- no context-switching to a separate tool
- Advanced search with complex query support

Source: [GitHub Issues](https://github.com/features/issues), [InfoQ: Evolving GitHub Issues](https://www.infoq.com/news/2025/02/github-issues/)

---

## 2. AI-Guided Planning: Current State of the Art

### 2.1 Kiro (AWS) -- Spec-Driven Development

Kiro is the most fully realized AI-guided planning tool, implementing a three-phase workflow:

**Phase 1: Requirements** (`requirements.md`)
- Generates user stories with acceptance criteria
- Uses EARS notation (Easy Approach to Requirements Syntax): `WHEN [condition/event] THE SYSTEM SHALL [expected behavior]`
- Focus: *what* the system should do, not *how*

**Phase 2: Design** (`design.md`)
- Technical architecture, sequence diagrams, API definitions
- Data flow, error handling, testing strategy
- Translates requirements into implementation approach

**Phase 3: Tasks** (`tasks.md`)
- Granular, sequenced tasks with dependencies
- Real-time status tracking during implementation
- Maps each task to acceptance criteria

**Best practices from Kiro docs:**
- Create multiple focused specs per feature, not one massive spec for the whole codebase
- Keep tasks focused and manageable
- Mark tasks as required vs. optional
- Requirements should describe *what*, not *how* -- leave architecture flexibility for the design phase
- Choose Requirements-First or Design-First upfront; do not switch mid-spec

**Critical insight from Martin Fowler's analysis:** Kiro's approach is "spec-first" (documentation precedes code, but specs may be discarded after feature completion), not "spec-anchored" or "spec-as-source." This is the right level for most development work.

Sources: [Kiro Docs: Specs](https://kiro.dev/docs/specs/), [Kiro Best Practices](https://kiro.dev/docs/specs/best-practices/), [Martin Fowler: Understanding SDD](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)

### 2.2 cc-sdd (Community Kiro for Claude Code)

The open-source `cc-sdd` project brings Kiro-style SDD to Claude Code and other AI assistants:
- `/kiro:spec-init` -- Initialize a feature specification
- `/kiro:spec-requirements` -- Generate requirements
- `/kiro:spec-design` -- Create technical design
- `/kiro:spec-tasks` -- Break into implementation tasks
- `/kiro:spec-impl` -- Execute with TDD
- Includes "steering" files for project memory (architecture, patterns, standards)

Source: [cc-sdd on GitHub](https://github.com/gotalab/cc-sdd)

### 2.3 Claude Code Plan Mode

Claude Code's native plan mode provides a lighter-weight alternative:
- **Shift+Tab twice** to enter plan mode
- Claude analyzes the codebase (read-only) and proposes a plan
- Developer reviews and refines before execution
- Best practice: **"Do not write any code yet. Just give me the plan."**
- **Context window management**: Start new sessions at 40-50% context utilization
- **Scope rule**: Plan what you will do in the next 30 minutes or less

**AskUserQuestion Tool for PRDs:**
Claude Code can conduct a structured interview to build a PRD:
- Round 1: Core workflow and technical foundation
- Subsequent rounds: UI/UX decisions, trade-offs, edge cases
- Output: `PRD.md` as source of truth for the AI agent
- Key: "The quality of your output is directly dictated by the precision of your input"

Sources: [Claude Code Common Workflows](https://code.claude.com/docs/en/common-workflows), [Claude Code Plan Mode Best Practices](https://cuong.io/blog/2025/07/15-claude-code-best-practices-plan-mode), [Stormy AI: AskUserQuestion for PRDs](https://stormy.ai/blog/claude-code-planning-ask-user-question-tool-prds)

### 2.4 ChatPRD

ChatPRD (100,000+ PM users) demonstrates the conversational PRD creation pattern:
- Starts with a basic concept, asks targeted questions about audience and features
- Iterative back-and-forth conversation refines the PRD
- Reviews documents "like a Chief Product Officer" -- identifying strategic gaps, questioning assumptions
- Pushes output to Linear, syncs with Notion, generates prototypes
- Purpose-built for product requirements with specific tuning and structure

Source: [ChatPRD](https://www.chatprd.ai/)

### 2.5 Martin Fowler's SDD Taxonomy

Fowler's team identified three levels of spec-driven development maturity:

| Level | Description | Current Reality |
|---|---|---|
| **Spec-first** | Documentation before code; specs discarded after feature completion | Kiro, most tools |
| **Spec-anchored** | Specs persist through maintenance; revised as features evolve | Tessl (exploring) |
| **Spec-as-source** | Humans edit only specs; code is generated. "DO NOT EDIT" markers. | Aspirational only |

Key skepticism: "Specification structures may amplify existing challenges like review overload." Agents frequently ignore instructions, and verbose markdown reviews feel burdensome compared to code review.

Source: [Martin Fowler: SDD Tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)

---

## 3. Value-First Thinking Frameworks

### 3.1 Jobs-to-be-Done (JTBD)

The JTBD framework focuses on **what the customer is trying to accomplish**, not what features to build. Adapted for developer workflows:

**The core question:** "When [situation], I want to [motivation], so I can [expected outcome]."

Applied to planning: Before any technical discussion, force the developer to articulate:
1. **Who** has this problem?
2. **What** are they trying to accomplish? (the "job")
3. **What** are they doing today? (current solution)
4. **Why** is today's solution inadequate? (pain/friction)
5. **What does success look like?** (measurable outcome)

JTBD + Agile insight: "Agile helps you develop a product faster and JTBD helps you develop the right product, so together you get the right product faster."

Sources: [ProductPlan JTBD](https://www.productplan.com/glossary/jobs-to-be-done-framework/), [First Round Review: Lightweight JTBD](https://review.firstround.com/build-products-that-solve-real-problems-with-this-lightweight-jtbd-framework/), [thrv: JTBD and Agile](https://www.thrv.com/blog/jobs-to-be-done-and-agile)

### 3.2 Opportunity Solution Trees (Teresa Torres)

Teresa Torres's OST framework provides a visual hierarchy for connecting business goals to solutions:

```
Desired Outcome (business value)
  |
  +-- Opportunity (customer need/pain point)
  |     +-- Solution A
  |     |     +-- Assumption Test
  |     +-- Solution B
  |           +-- Assumption Test
  |
  +-- Opportunity (another customer need)
        +-- Solution C
              +-- Assumption Test
```

**Four layers:**
1. **Desired Outcome** -- measurable business value ("reduce churn by 10%")
2. **Opportunities** -- customer needs, pain points, desires
3. **Solutions** -- products, features, or services
4. **Assumption Tests** -- validation experiments

**Why this matters for our workflow:** It forces the question "what outcome are we driving?" before "what should we build?" and reveals when multiple solutions could serve the same opportunity.

Source: [ProductTalk: Opportunity Solution Trees](https://www.producttalk.org/opportunity-solution-trees/)

### 3.3 Impact Mapping (Gojko Adzic)

Impact mapping asks four questions in sequence:

1. **WHY?** -- What is the business goal?
2. **WHO?** -- Who are the actors that can help or hinder?
3. **HOW?** -- How should their behavior change?
4. **WHAT?** -- What can we deliver to cause that change?

This creates a natural funnel from abstract business goals to concrete deliverables. The key principle: "a tremendous amount of time and money is wasted due to wrong assumptions, lack of focus, poor communication of objectives."

Source: [Impact Mapping](https://www.impactmapping.org/book.html), [Gojko Adzic](https://gojko.net/books/impact-mapping/)

### 3.4 Synthesis: The Value-First Question Stack

Combining JTBD, OST, and Impact Mapping yields a minimal question stack:

| # | Question | Framework Origin | Purpose |
|---|---|---|---|
| 1 | What problem does this solve? | JTBD | Ground in reality |
| 2 | Who has this problem? | Impact Mapping | Identify stakeholders |
| 3 | What are they doing today? | JTBD | Understand current state |
| 4 | What outcome would success produce? | OST | Define measurable value |
| 5 | What is the simplest solution? | Shape Up appetite | Constrain scope |
| 6 | What should we NOT build? | Shape Up no-gos | Prevent scope creep |

---

## 4. Lean Task Decomposition

### 4.1 The Minimal Viable Structure

Research across Shape Up, Linear, Kiro, and modern product teams converges on this hierarchy:

```
Epic (= the shaped pitch / feature spec)
  |
  +-- Task 1 (concrete, completable in <4 hours)
  +-- Task 2
  +-- Task 3
  ...
```

**Key insight: Skip the "story" layer for most work.** Stories are useful for cross-team communication but add overhead for individual developers or small teams. Linear explicitly recommends against them. Shape Up does not use them at all during the build phase.

### 4.2 What Makes a Good Task?

Synthesizing across all sources:

| Property | Description | Source |
|---|---|---|
| **Completable** | Can be finished in one sitting (1-4 hours) | Kiro, Shape Up |
| **Verifiable** | Has a clear "done" condition | Kiro (acceptance criteria mapping) |
| **Independent** | Can be worked on without waiting for other tasks (ideal) | cc-sdd (parallel execution) |
| **Concrete** | Describes what to do, not what to think about | Linear Method |
| **Ordered** | Dependencies are explicit when they exist | Kiro tasks.md |

### 4.3 Linear's Issue Format (Minimal)

```
Title: [Verb] [thing] [context]
Description (optional): Brief context, links to discussion, constraints
Labels: bug | feature | improvement | chore
Priority: urgent | high | medium | low
```

Example:
```
Title: Add rate limiting to blob/add endpoint
Description: Currently no rate limiting on blob/add. Add 100 req/min
per space. See #discussion-423 for context.
Priority: high
```

### 4.4 Shape Up's Approach: No Tasks Upfront

Shape Up takes the most radical position: **teams discover tasks during building, not during planning.** The shaped pitch provides direction and boundaries; the team figures out the specific tasks as they go, using a "hill chart" to track progress from "figuring things out" to "making it happen."

This works because Shape Up teams are experienced and autonomous. For AI-assisted development, we need slightly more structure because the AI needs explicit tasks to execute against.

---

## 5. Anti-Patterns: What Makes Planning a Burden

### 5.1 The Planning Overhead Trap

Based on research across agile anti-patterns, developer experience studies, and practitioner writing:

**Process anti-patterns that kill adoption:**

| Anti-Pattern | Why Developers Skip It | Fix |
|---|---|---|
| **Template overload** | 15-field JIRA tickets with mandatory fields | Require only title + 1-2 fields |
| **User story theater** | "As a user I want to..." for internal tooling | Write plain-language issues (Linear) |
| **Estimation rituals** | Story pointing that never maps to reality | Use appetite/time-boxing (Shape Up) |
| **Spec-then-forget** | Document nobody reads after writing | Spec is the AI's source of truth (Kiro) |
| **Premature decomposition** | Breaking work into tasks before understanding it | Shape first, decompose during build |
| **Review overload** | Verbose markdown specs that require lengthy reviews | Keep specs to 1 page (one-pager philosophy) |
| **Tool fragmentation** | Planning in one tool, coding in another | Keep planning in the terminal/IDE |
| **Ceremony creep** | Standups + planning + grooming + retro + demo | Async by default (37signals) |

### 5.2 What Developers Actually Want

From the SPACE framework research and developer experience studies:

- **Flow state preservation** -- planning should not break flow; it should establish it
- **Autonomy** -- "tell me the problem and the boundaries, not the steps"
- **Context** -- "give me enough to start, not a 30-page PRD"
- **Progress visibility** -- "I want to see what is done and what is next"
- **Low switching cost** -- "do not make me leave my editor"

### 5.3 The Goldilocks Zone

```
Too Little Planning          Just Right              Too Much Planning
|                            |                       |
"vibe coding"                "shaped work"           "analysis paralysis"
no direction                 clear problem +         50-page PRDs
rework cycles                constrained solution    estimation theater
"what am I building?"        + explicit no-gos       "when can I code?"
                             10-30 min planning      days of planning
                             for days of coding      for days of coding
```

---

## 6. Research: Planning vs. Productivity

### 6.1 The SPACE Framework (Forsgren et al., 2021)

The SPACE framework from Microsoft Research and GitHub identifies five dimensions of developer productivity:

- **S**atisfaction and well-being
- **P**erformance
- **A**ctivity
- **C**ommunication and collaboration
- **E**fficiency and flow

Key finding: **Productivity cannot be measured by a single metric.** Activity (lines of code, commits) is the least reliable indicator. Flow, satisfaction, and the quality of collaboration matter more.

**Implication for planning:** Planning that improves developer satisfaction, enables flow state, and reduces communication friction is genuinely productive -- even though it "looks like" not coding.

Source: [SPACE Framework (ACM Queue)](https://queue.acm.org/detail.cfm?id=3454124), [Microsoft Research](https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/)

### 6.2 Defect Cost Research

Research consistently shows:
- **64% of total defect costs** originate in requirements and design phases
- Fixing a requirements defect costs **10-100x more** in production than during planning
- Future Scenarios (thinking through edge cases upfront) reduce "ambiguities, contradictions and lack of clarity"

This argues strongly for *some* upfront thinking -- but not for exhaustive specification.

Source: [iSixSigma: Defect Prevention](https://www.isixsigma.com/software/defect-prevention-reducing-costs-and-enhancing-quality/)

### 6.3 Team Size and Planning Overhead

Research from QSM and others:
- Teams of **1.5-7 people** show the highest productivity indices
- Smaller teams need **less planning overhead** because communication costs are lower
- Recommended planning allocation: **10-20%** of total project time
- Elite teams spend about 20% on planning; mediocre teams spend either <5% or >30%

For a solo developer or pair working with an AI assistant, the optimal planning allocation is at the low end: **5-15 minutes of structured thinking per feature, not hours.**

Source: [QSM: Team Size](https://www.qsm.com/team-size-can-be-key-successful-software-project), [Hypersense: Effort Allocation](https://hypersense-software.com/blog/2025/07/19/software-development-effort-allocation-dev-qa-design-pm-ratio/)

### 6.4 DORA Metrics and AI

The 2025 DORA Report found that:
- AI adoption **improves throughput** but **increases delivery instability**
- Seven critical capabilities needed before AI tools deliver full value
- Speed and stability **correlate positively** (they are not trade-offs)

**Implication:** AI-assisted planning must explicitly address stability (edge cases, error handling, testing) -- not just speed of task completion.

Source: [DORA](https://dora.dev/guides/dora-metrics/)

---

## 7. Recommended Workflow Design

### 7.1 Design Principles

Based on all research, the workflow should follow these principles:

1. **Conversational, not form-filling.** The AI asks questions; the developer answers in natural language. No templates to fill out.
2. **Value-first, always.** The first questions are about WHY and WHO, never about HOW.
3. **Time-boxed.** The entire planning conversation should take 5-15 minutes for a typical feature.
4. **Produces artifacts the AI uses.** The output is not documentation for humans to read -- it is a spec the AI executes against. This gives planning immediate, tangible value.
5. **Scales with complexity.** Simple bug fix = 2 questions. New feature = 6-8 questions. Major architectural change = full spec.
6. **Lives in the repo.** Output is a markdown file in the project, not in a separate tool.
7. **Progressive disclosure.** Start minimal, go deeper only when the developer's answers reveal complexity.

### 7.2 The Three-Tier Planning Model

```
Tier 1: QUICK (2-3 minutes)
  For: Bug fixes, small improvements, clear tasks
  Questions: What? Why? Any gotchas?
  Output: A single task with context

Tier 2: STANDARD (5-10 minutes)
  For: New features, significant changes
  Questions: Problem, user, outcome, solution, scope, risks
  Output: Feature brief + task list (3-8 tasks)

Tier 3: FULL (15-25 minutes)
  For: Architectural changes, new systems, cross-cutting concerns
  Questions: All of Tier 2 + technical design, migration strategy, rollback plan
  Output: Feature brief + design notes + task list (5-15 tasks)
```

The AI should **auto-detect the tier** based on the developer's initial description, then confirm: "This sounds like a [new feature / bug fix / architectural change]. I'll ask you [N] quick questions to make sure we build the right thing. Sound good?"

### 7.3 The Conversation Flow

```
Developer: "I want to build X"
           |
           v
    [AI detects complexity tier]
           |
           v
    Phase 1: VALUE (2-4 questions)
    - What problem does this solve?
    - Who benefits?
    - What does success look like?
    - What's the appetite (time budget)?
           |
           v
    Phase 2: SCOPE (2-4 questions)
    - What's the simplest version that solves the problem?
    - What should we explicitly NOT build?
    - Any known rabbit holes or risks?
    - Are there existing patterns to follow?
           |
           v
    Phase 3: TASKS (AI-generated, developer-approved)
    - AI generates ordered task list
    - Developer reviews and adjusts
    - AI begins execution
```

### 7.4 Adaptive Intelligence

The AI should adapt its questioning based on context:

- **Codebase awareness:** If the developer says "add rate limiting to the API," and the AI can see the existing middleware patterns, it should ask about those patterns rather than generic architecture questions.
- **Project memory:** If a `CLAUDE.md` or steering file exists, use it to skip questions about tech stack, conventions, and architecture.
- **Previous specs:** If similar features have been built before, reference them: "I see you built something similar for blob/add. Should this follow the same pattern?"
- **Skip what is obvious:** If the developer's initial description already answers a question, do not ask it again.

---

## 8. Example Question Flows

### 8.1 Tier 1: Bug Fix

```
Developer: "The blob/add endpoint returns 500 when the CAR file is empty"

AI: "Got it -- a bug fix. Let me confirm a few things:

1. What should happen when an empty CAR is submitted?
   (a) Return a 400 with a clear error message
   (b) Accept it silently (empty upload)
   (c) Something else?

2. Is this causing issues in production right now, or did you find
   it during testing?

3. Any related endpoints that might have the same issue?"

[Developer answers]

AI: "Here's my plan:
- [ ] Add empty CAR validation in blob/add handler
- [ ] Return 400 with `CarFileEmpty` error
- [ ] Add test case for empty CAR submission
- [ ] Check blob/remove for same issue (you mentioned it might)

Ready to start?"
```

### 8.2 Tier 2: New Feature

```
Developer: "I want to add egress tracking to the gateway so we can
bill storage nodes for bandwidth"

AI: "Interesting -- that touches billing, so let me make sure we
get the scope right.

1. PROBLEM: What's happening today? Are storage nodes using
   bandwidth without being tracked, or is there tracking that's
   not connected to billing?

2. USERS: Who sees the billing data? Node operators via a
   dashboard? Internal finance team? API consumers?

3. OUTCOME: What does success look like? A specific metric you
   want to see? 'We can generate a monthly invoice per storage
   node'?

4. APPETITE: How much time should we invest? Is this a focused
   week of work, or something bigger?"

[Developer answers each]

AI: "A few more questions to nail down scope:

5. SCOPE: I see the gateway already has 26 middlewares. Should
   egress tracking be a new middleware, or extend an existing
   one? (I found `withEgressTracker` in the middleware stack --
   is that related?)

6. NO-GOS: Anything we should explicitly NOT do in v1?
   (e.g., real-time billing vs. batch processing?)

7. RISKS: The etracker service is in Go and the gateway is a
   CF Worker. How should they communicate? Are there existing
   patterns for this?"

[Developer answers]

AI: "Here's the feature brief and task list:

## Egress Tracking for Gateway Billing

**Problem:** Storage nodes consume bandwidth through Freeway
gateway but usage isn't tracked, preventing accurate billing.

**Success:** Monthly egress report per storage node, accurate
to within 1% of actual bytes served.

**Appetite:** 1 week (5 working days)

**No-gos:** No real-time billing dashboard in v1. Batch
processing is fine.

### Tasks
- [ ] Add egress counting middleware to Freeway (after response)
- [ ] Define egress event schema (node DID, bytes, timestamp, CID)
- [ ] Send egress events to etracker service via existing queue
- [ ] Add etracker endpoint to aggregate by node + time period
- [ ] Add integration test with mock gateway traffic
- [ ] Add monthly report generation query

### Rabbit Holes
- Range requests: count actual bytes returned, not content-length
- Cached responses: decide whether to count or skip (recommend: count)
- Error responses: do not count 4xx/5xx egress

Shall I start with the first task?"
```

### 8.3 Tier 3: Architectural Change

```
Developer: "We need to migrate from DynamoDB to a different
storage backend for content claims"

AI: "That's a significant architectural change. Let me walk
through this carefully -- about 8 questions, should take 10
minutes.

VALUE:
1. What's driving this migration? Cost? Performance limits?
   Feature requirements DynamoDB can't support?

2. What outcome would make this migration worth the effort?
   (e.g., '10x query performance' or 'save $X/month')

3. What's the appetite? Is this a focused sprint or a gradual
   migration over multiple cycles?

SCOPE:
4. I see content-claims has [N] DynamoDB tables. Are we
   migrating all of them or starting with a subset?

5. What's the target storage backend? Have you evaluated
   options, or do you need help comparing?

6. What's the migration strategy? Big bang cutover, or
   dual-write with gradual migration?

RISK:
7. Content claims is used by [list dependent services].
   What's the rollback plan if the migration has issues?

8. Are there any data format changes, or is this purely a
   backend swap with the same API surface?"

[Developer answers all 8]

AI: [Generates full feature brief + design notes + 12-15 tasks
     with explicit dependency ordering and migration phases]
```

---

## 9. Recommended Templates

### 9.1 Feature Brief (The Only Required Output)

```markdown
# [Feature Name]

## Problem
[1-3 sentences: what's broken or missing, and for whom]

## Success
[1 sentence: measurable outcome when this is done]

## Appetite
[Time budget: "2 days" / "1 week" / "2 weeks"]

## Solution
[2-5 sentences: the approach, referencing existing patterns]

## No-gos
- [Thing we will NOT build]
- [Another thing we will NOT build]

## Tasks
- [ ] [Concrete, completable task]
- [ ] [Another task]
- [ ] [Another task]

## Risks
- [Known rabbit hole or edge case]
```

**This is ~20 lines of markdown.** It takes 5-10 minutes to produce conversationally. It gives the AI everything it needs to execute.

### 9.2 Task Format (Minimal)

```
- [ ] [Verb] [thing] [in context] [constraint if any]
```

Good examples:
```
- [ ] Add validation for empty CAR files in blob/add handler
- [ ] Create egress event schema matching etracker's existing format
- [ ] Write integration test covering range request byte counting
```

Bad examples:
```
- [ ] Research best practices for validation  (too vague)
- [ ] Implement the thing we discussed        (no context)
- [ ] Set up infrastructure                   (too broad)
```

### 9.3 Extended Template for Tier 3 (Architectural Changes)

Add these sections to the feature brief:

```markdown
## Design Notes
[Technical approach: architecture, data flow, key interfaces]

## Migration Strategy
[How we get from current state to target state safely]

## Rollback Plan
[What happens if this goes wrong]

## Dependencies
[What must be done first, what this blocks]
```

---

## 10. Must-Have vs. Nice-to-Have

### MUST HAVE (Core workflow that ships first)

| Element | Rationale |
|---|---|
| **Complexity auto-detection** | AI tiers the planning depth to match the work |
| **Value-first questions** | "What problem? Who benefits? What does success look like?" before any technical questions |
| **Appetite/time-box** | Forces scope constraint. Without this, everything becomes a boil-the-ocean project |
| **No-gos / explicit exclusions** | Single most effective anti-scope-creep tool across all methodologies |
| **Concrete task generation** | The AI produces ordered, verifiable tasks the developer approves |
| **Feature brief output** | A single markdown artifact (< 1 page) that serves as AI execution context |
| **Codebase awareness** | AI references existing patterns, files, and conventions in its questions |
| **Skip-what's-obvious** | If the developer's initial message answers questions, do not re-ask them |

### NICE TO HAVE (Iterate toward these)

| Element | Rationale |
|---|---|
| **Project memory / steering files** | Persistent context about architecture, conventions, past decisions |
| **Rabbit hole detection** | AI proactively identifies risks based on codebase analysis |
| **Progress tracking** | Hill chart or checklist-style progress visualization |
| **Spec persistence** | Specs saved as markdown files in the repo for future reference |
| **Cross-feature awareness** | AI notices when new work overlaps with existing specs |
| **Design notes for complex work** | Sequence diagrams, interface definitions for Tier 3 work |
| **Template customization** | Teams configure their own question flows and output formats |
| **Dependency mapping** | Tasks with explicit blocking relationships |

### EXPLICITLY NOT (Things that would make this feel heavy)

| Element | Why to Avoid |
|---|---|
| Story points / estimation | Research shows these rarely map to reality; appetite is sufficient |
| Mandatory fields beyond title | Every required field is friction; keep most things optional |
| Separate tool / UI | Must live in the terminal/IDE where developers already work |
| Multi-step approval workflow | One person (the developer) approves and goes; no review chains |
| Sprint/cycle ceremony | The developer decides when to plan and when to code |
| Formal acceptance criteria format | "GIVEN/WHEN/THEN" is fine if the developer likes it; never required |

---

## 11. Sources

### Methodologies and Frameworks

- [Shape Up: Write the Pitch](https://basecamp.com/shapeup/1.5-chapter-06) -- Ryan Singer, Basecamp
- [Shape Up: Risks and Rabbit Holes](https://basecamp.com/shapeup/1.4-chapter-05) -- Ryan Singer, Basecamp
- [Shape Up: Full Book (PDF)](https://basecamp.com/shapeup/shape-up.pdf) -- Ryan Singer
- [37signals: Shape Up Every Six](https://37signals.com/06) -- 37signals
- [Linear Method: Principles & Practices](https://linear.app/method/introduction) -- Linear
- [Write Issues, Not User Stories](https://linear.app/method/write-issues-not-user-stories) -- Linear Method
- [Impact Mapping](https://www.impactmapping.org/book.html) -- Gojko Adzic
- [Opportunity Solution Trees](https://www.producttalk.org/opportunity-solution-trees/) -- Teresa Torres, ProductTalk
- [JTBD Framework](https://www.productplan.com/glossary/jobs-to-be-done-framework/) -- ProductPlan
- [Lightweight JTBD Framework](https://review.firstround.com/build-products-that-solve-real-problems-with-this-lightweight-jtbd-framework/) -- First Round Review
- [JTBD and Agile, Better Together](https://www.thrv.com/blog/jobs-to-be-done-and-agile) -- thrv

### AI-Guided Planning Tools

- [Kiro: Specs Documentation](https://kiro.dev/docs/specs/) -- AWS Kiro
- [Kiro: Best Practices](https://kiro.dev/docs/specs/best-practices/) -- AWS Kiro
- [Kiro: From Chat to Specs](https://kiro.dev/blog/from-chat-to-specs-deep-dive/) -- AWS Kiro Blog
- [Understanding SDD: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) -- Martin Fowler / Birgitta Boeckeler
- [cc-sdd: Kiro-Style SDD for Claude Code](https://github.com/gotalab/cc-sdd) -- gotalab (GitHub)
- [ChatPRD](https://www.chatprd.ai/) -- ChatPRD
- [Claude Code Common Workflows](https://code.claude.com/docs/en/common-workflows) -- Anthropic
- [Claude Code Plan Mode Best Practices](https://cuong.io/blog/2025/07/15-claude-code-best-practices-plan-mode) -- Code Centre
- [Claude Code AskUserQuestion for PRDs](https://stormy.ai/blog/claude-code-planning-ask-user-question-tool-prds) -- Stormy AI
- [Spec-Driven Development: Tools and Best Practices](https://www.marvinzhang.dev/blog/sdd-tools-practices) -- Marvin Zhang

### Engineering Culture

- [Vercel: Improving Developer Workflow](https://vercel.com/blog/improving-developer-workflow) -- Vercel
- [How Vercel Measures Developer Productivity](https://getdx.com/customers/vercel/) -- DX / Vercel
- [37signals Dev: The 10x Development Environment](https://dev.37signals.com/the-10x-development-environment/) -- 37signals
- [How We Work](https://basecamp.com/handbook/how-we-work) -- Basecamp Handbook
- [GitHub Issues: Project Planning for Developers](https://github.com/features/issues) -- GitHub
- [Evolving GitHub Issues](https://www.infoq.com/news/2025/02/github-issues/) -- InfoQ

### Research and Productivity Studies

- [The SPACE of Developer Productivity](https://queue.acm.org/detail.cfm?id=3454124) -- Forsgren, Storey, Maddila, Zimmermann, Houck, Butler (ACM Queue, 2021)
- [SPACE Framework (Microsoft Research)](https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/) -- Microsoft Research
- [DORA Metrics](https://dora.dev/guides/dora-metrics/) -- DORA / Google
- [Team Size and Software Project Success](https://www.qsm.com/team-size-can-be-key-successful-software-project) -- QSM
- [Software Development Effort Allocation](https://hypersense-software.com/blog/2025/07/19/software-development-effort-allocation-dev-qa-design-pm-ratio/) -- Hypersense Software
- [Defect Prevention: Reducing Costs](https://www.isixsigma.com/software/defect-prevention-reducing-costs-and-enhancing-quality/) -- iSixSigma
- [Requirements Engineering in Large-Scale Agile](https://www.sciencedirect.com/science/article/pii/S0164121220302417) -- ScienceDirect
- [Empirical Findings on Team Size and Productivity](https://www.researchgate.net/publication/228838549_Empirical_Findings_on_Team_Size_and_Productivity_in_Software_Development) -- ResearchGate
- [Software Productivity in Practice: A Systematic Mapping Study](https://www.mdpi.com/2674-113X/1/2/8) -- MDPI

### Anti-Patterns and Process Design

- [The 37signals Planning Philosophy Mistake](https://thesambarnes.com/planning/the-37signals-planning-philosophy-mistake/) -- Sam Barnes
- [7 Lessons from Trialling Shape Up](https://www.mindtheproduct.com/7-lessons-from-trialling-basecamps-shape-up-methodology/) -- Mind the Product
- [Agile Anti-Patterns](https://fastercapital.com/content/Agile-Anti-patterns--How-to-Avoid-and-Overcome-Common-Pitfalls-in-Agile-Development.html) -- FasterCapital
- [Shape Up: Should You Change Your Methodology?](https://marmelab.com/blog/2024/09/26/shape-up.html) -- Marmelab (2024)

---

## Appendix: Comparison Matrix of Planning Approaches

| Approach | Planning Time | Output | Structure Level | AI-Compatible | Developer Adoption |
|---|---|---|---|---|---|
| **Shape Up Pitch** | 30-60 min | 1-page pitch | Medium | Moderate | High (for shapers) |
| **Linear Issues** | 2-5 min/issue | Title + optional description | Minimal | High | Very High |
| **Kiro SDD** | 15-30 min | 3 markdown files | High | Native | Medium |
| **Claude Plan Mode** | 5-15 min | Plan in chat | Low-Medium | Native | High |
| **JIRA Epic/Story/Task** | 1-4 hours | Structured tickets | Very High | Low | Low |
| **GitHub Issues + Sub-issues** | 5-10 min | Issue + checklist | Low-Medium | High | High |
| **Our Recommended Workflow** | **5-15 min** | **Feature brief + tasks** | **Adaptive** | **Native** | **Target: Very High** |

The sweet spot is clear: **5-15 minutes of conversational planning producing a feature brief with concrete tasks**, where the AI uses the brief as execution context. This matches the planning overhead research (5-15% of coding time), avoids the anti-patterns developers hate, and produces artifacts that immediately accelerate the coding that follows.
