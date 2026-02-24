# Storacha AI Development Process Guide

A structured workflow for AI-assisted development using Claude Code. Designed to prevent spec drift, enforce test-driven development, and keep the human in control.

---

## How It Works (TL;DR)

Every feature goes through **5 phases** in strict order. The AI cannot skip phases — enforcement hooks block it. The human approves at every phase transition.

```
SPECIFY → DESIGN → DECOMPOSE + TEST → IMPLEMENT → COMPLETE
   ↑          ↑           ↑                ↑           ↑
 brief     design      tasks +          code +      PR +
  .md       notes    failing tests    passing tests  review

   🔒 Human approval gate at each arrow 🔒
```

---

## Phase 1: SPECIFY

**Goal:** Understand *what* to build and *why*, before touching any code.

**What happens:**
- AI asks value-first questions: What problem? Who benefits? What does success look like?
- AI produces a **feature brief** (`brief.md`) with testable acceptance criteria
- Human reviews and approves the brief

**What the AI cannot do:** Write any code or design files. Plan mode only.

**Key artifact:** `brief.md` — the single source of truth for the feature.

---

## Phase 2: DESIGN

**Goal:** Explore the codebase read-only. Figure out *where* and *how* to implement.

**What happens:**
- AI reads existing code, finds patterns to follow, identifies files to change
- Produces design notes (which files, which interfaces, what data flows)
- Human reviews and approves the design

**What the AI cannot do:** Create or modify any source files. Read-only exploration.

**Key artifact:** Design notes (in `brief.md` or separate `design.md` for large features).

**Skipped for Tier 1** (small bug fixes with known cause).

---

## Phase 3: DECOMPOSE + TEST

**Goal:** Break the work into tasks and write acceptance tests *before* any implementation.

**What happens:**
1. AI breaks the feature into small tasks (1-2 files each), with explicit dependencies
2. A **separate AI agent** (isolated context) writes acceptance tests based only on the brief — it never sees implementation details
3. All tests are verified to **FAIL** (red) — proving they actually test something
4. Human reviews the task list and tests

**What the AI cannot do:** Write any source code. Test files only.

**Why a separate agent writes tests:** The implementing agent has an incentive to write easy-to-pass tests. Context isolation prevents this. A "subagent attestation" file proves the tests were written independently.

**Key artifacts:**
- `tasks.md` — ordered task list with dependencies
- Test files — the executable definition of "done"
- `tests-snapshot/` — frozen copy of tests for tampering detection

---

## Phase 4: IMPLEMENT

**Goal:** Write code to make all tests pass. One task at a time, TDD red-green-refactor.

**What happens:**
1. AI picks the next unblocked task (respects dependency order)
2. Quotes the acceptance criteria it's implementing (prevents drift)
3. Writes unit tests (red) → implements minimal code (green) → refactors
4. Self-audits against acceptance criteria after each task
5. After ALL tasks pass → a **separate AI agent** performs code review

**What the AI cannot do:**
- Modify acceptance tests from Phase 3 (they are **frozen**)
- Start a task whose dependencies aren't complete
- Skip the final code review

**Test dispute process:** If the AI thinks a test is wrong, it must STOP and spawn an independent reviewer agent. The reviewer decides — the implementer never modifies its own tests.

**Stop triggers** (AI must halt and report):
- Task needs more files than planned
- Undocumented dependency discovered
- High-blast-radius package change needed
- 3+ failed approaches for same test

**Key artifact:** `reviews/final.json` — independent code review result.

---

## Phase 5: COMPLETE

**Goal:** Ship the code. Human reviews on GitHub.

**What happens:**
1. AI commits to `feat/{feature-slug}` branch
2. Creates a **draft PR** with deliverable summary
3. Human reviews on GitHub (inline comments, request changes, or approve)
4. If changes requested → **feedback loop** (see below)
5. After approval + merge → spec moves to `.specs/done/`

**Feedback loop (3-agent system):**
1. **Feedback Validator** — reads PR comments, classifies as actionable / contradicts spec / unclear. Can push back if feedback conflicts with accepted criteria.
2. **Execution Agent** — implements fixes, pushes fixup commits (never force-push)
3. **Code Reviewer** — reviews only the new commits

Human uses GitHub's "Changes since last review" to see only the delta.

---

## Complexity Tiers

Not every change needs the full workflow. The AI auto-detects complexity:

| Tier | Scope | Process |
|------|-------|---------|
| **0: Trivial** | Typo, config, 1-2 files | Just do it. No spec needed. |
| **1: Quick** | Bug fix, 2-5 files | Brief → Skip Design → Tests → Implement |
| **2: Standard** | New feature, 5-15 files | Full 5-phase workflow |
| **3: Full** | Cross-service, 10+ files | Full workflow + architecture doc |

**Tier 0 sanity check:** Even "trivial" changes escalate to Tier 1 if they touch blast-radius packages, capability schemas, or 3+ files.

---

## Enforcement: How We Prevent the AI from Cutting Corners

Three layers of defense:

### Layer 1: Rules (~60-80% compliance)
Written instructions in `.claude/rules/`. The AI follows them by default but can drift under pressure.

### Layer 2: Hooks (~90%+ compliance)
Shell scripts that **block** tool calls that violate the process:

| Hook | What it blocks |
|------|---------------|
| `phase-gate.sh` | Source files in specify/design phases, non-test files in decompose |
| `tdd-guard.sh` | Source file edits if no test snapshot exists |
| `test-mod-detector.sh` | Warns when acceptance tests are modified during implement |
| `branch-protection.sh` | Commits to main when a feature branch is active |
| `pre-commit-checks.sh` | Commits before implement/complete phase |
| `review-gate.sh` | Phase transitions without required review artifacts |
| `process-guard.sh` | Process file changes without an accepted AIPIP |
| `session-resume.sh` | (Non-blocking) Re-injects feature state on session resume |
| `workflow-nudge.sh` | (Non-blocking) Injects phase context into every prompt |

### Layer 3: Human Review Gates
Mandatory approval at every phase transition. The AI asks and waits.

---

## Blast Radius Awareness

Some packages affect 10-15+ repos. The AI checks before changing them:

**EXTREME caution (15+ repos):** `@ucanto/core`, `@ucanto/interface`, `@ucanto/principal`, `@ucanto/transport`, `@ipld/car`

**HIGH caution (10+ repos):** `@storacha/capabilities`, `@storacha/client`, `go-ucanto`, `go-libstoracha`

**Rule:** Adding new capabilities = safe. Changing existing capability schemas = dangerous.

The AI runs `python aidev/tools/query.py impact <package>` before touching shared packages.

---

## Process Governance (AIPIPs)

The process itself is versioned and governed. To change any rule, hook, or skill:

1. Write an **AIPIP** (AI Process Improvement Proposal) — formal document with problem, proposal, alternatives, impact
2. Human reviews and accepts
3. Only then can process files be modified (enforced by `process-guard.sh`)

This prevents the AI from silently weakening its own constraints under task pressure.

10 AIPIPs have been accepted so far, each improving the workflow based on real usage.

---

## Slash Commands

| Command | What it does |
|---------|-------------|
| `/dev` | Start the full development workflow for a feature |
| `/trace <flow>` | Load an end-to-end flow trace (upload, retrieval, auth, etc.) |
| `/impact <pkg>` | Check blast radius before changing a shared package |
| `/spec <name>` | Show spec-to-implementation mapping |
| `/review` | Run code review (independent subagent) |
| `/new-capability` | Step-by-step guide for adding a UCAN capability |
| `/discover-repo` | Systematically explore a repo's structure |

---

## Key Principles

1. **Tests are the spec.** Acceptance tests define "done." The implementer cannot change them.
2. **Context isolation prevents bias.** Test-writers and code-reviewers work in separate AI contexts from the implementer.
3. **Human stays in control.** Mandatory approval gates at every phase. The AI asks, never assumes.
4. **Code over specs.** When implementation and spec disagree, follow the implementation. Flag the divergence.
5. **Pattern over principle.** Follow how the codebase already does things. Don't invent new patterns.
6. **Measure twice, cut once.** Trace before coding. Check blast radius. Stop and re-plan when complexity surprises you.
