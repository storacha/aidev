---
id: AIPIP-0001
title: Knowledge System v2 — Research-Backed Improvements
status: done
created: 2026-02-19
created-by: alex
last-updated: 2026-02-20
updated-by: claude
supersedes: null
superseded-by: null
---

# AIPIP-0001: Knowledge System v2 — Research-Backed Improvements

## Context

The current 5-layer knowledge system (CLAUDE.md → memory files → per-repo CLAUDE.md → slash commands → query tool) was adversarially evaluated against published best practices from Anthropic, Martin Fowler, D3 Framework, METR study, Kiro/spec-kit/Tessl, and others. Overall architecture is sound (avg 7.7/10), but specific gaps were identified.

**Research sources:** 9 research streams completed 2026-02-19:
1. AI codebase knowledge best practices (40+ sources)
2. External protocol specifications (14 technologies)
3. Spec-driven development workflows (20+ sources, Kiro/spec-kit/Tessl/cc-sdd)
4. Claude Code auto-activation mechanics
5. Lean PRD/planning workflows (40+ sources, Shape Up/Linear/JTBD/OST/Impact Mapping)
6. Workflow benchmarking against industry tools (Kiro, spec-kit, cc-sdd, Cursor, Windsurf, Copilot, BMAD)
7. TDD with AI agents (WebApp1K, TDFlow, Anthropic, Kent Beck, Nagappan et al.)
8. AI procedure enforcement (30+ sources, IFScale, Claude Code hooks, TDD Guard, Superpowers, CSDD)
9. Scanner data coverage + MCP for structured domain knowledge (Nx, Sourcegraph, arXiv 2601.08773, Speakeasy)

**Full research reports:** `research/lean-prd-workflow.md` (lean PRD), `research/tdd-ai-agents.md` (TDD), `research/enforcement-mechanisms.md` (enforcement), `research/scanner-data-coverage.md` (scanner/MCP), agent transcripts for others

## Scorecard (Pre-Improvement Baseline)

| Dimension | Score | Key Gap |
|---|---|---|
| Root instruction file design | 8/10 | Missing `.claude/rules/` modularization |
| Knowledge architecture | 8/10 | Missing MCP integration, live fallback |
| Brownfield readiness | 9/10 | No reviewer/verifier pattern |
| Knowledge freshness | 4/10 | No automation, no staleness detection |
| Multi-repo support | 7/10 | 61/82 repos uncovered |
| Context optimization | 7/10 | Missing subagent guidance, TL;DRs |

## Improvements

### Phase A: Quick Wins (Low Effort, High Impact)

#### A1. Add staleness headers to all memory files
- **Status:** `done`
- **What:** Add `<!-- Last validated: YYYY-MM-DD | Source: commit/tag/version -->` to each memory/tech/, memory/flows/, memory/architecture/ file
- **Why:** Freshness score 4/10 — biggest gap. No way to know when knowledge was last verified.
- **Effort:** Small (27 files, mechanical edit)
- **Files:** All `memory/**/*.md`

#### A2. Add external spec reference links to memory/tech/ files
- **Status:** `done`
- **What:** Add a `## Authoritative Specs` section to each tech file with canonical URLs from the protocol specs research
- **Why:** Grounds knowledge base in external authority; helps devs verify against specs
- **Effort:** Small (12 tech files)
- **Files:** `memory/tech/*.md`
- **Data source:** Protocol specs research (agent aceca37)

#### A3. Add TL;DR summaries to memory files
- **Status:** `done`
- **What:** Add 3-5 line summary block at top of each file for quick lookup
- **Why:** Context optimization — Claude can get a quick answer without loading full file (1000-3000 token sweet spot per loaded chunk)
- **Effort:** Small-medium (27 files)
- **Files:** All `memory/**/*.md`

#### A4. Create `.claude/rules/` directory with path-scoped rules
- **Status:** `done`
- **What:** Create always-loaded rule files that activate based on file path context:
  - `.claude/rules/conventions.md` — naming, imports, error handling
  - `.claude/rules/blast-radius.md` — package caution tiers
  - `.claude/rules/javascript.md` — JS/TS conventions (active when editing .ts/.js)
  - `.claude/rules/golang.md` — Go conventions (active when editing .go)
- **Why:** Rules are always loaded (like CLAUDE.md) but modular; path-scoped activation reduces noise
- **Effort:** Small (extract from existing CLAUDE.md + memory files)
- **Files:** `.claude/rules/*.md`

#### A5. Backfill scanner data into memory files
- **Status:** `done`
- **What:** Close the highest-value gaps between scanner structural data and memory narrative files. The memory files were written independently from scanner data and have major blind spots.
- **Why:** Analysis revealed memory files cover only 9% of service graph edges, 0% of SQL schemas, 0% of Go service infra, 23% of capability schemas. Developers working on Go services (Piri, Guppy, Storoku, Indexing-service) have zero infrastructure context in the knowledge base.
- **Effort:** Medium (research + write 3-4 sections across existing files)
- **Files:** `memory/architecture/infrastructure-decisions.md` (edit), `memory/architecture/shared-packages.md` (edit), `memory/tech/ucanto-framework.md` (edit), `memory/tech/go-ecosystem.md` (edit)
- **Depends on:** B2 (deferred — use `python tools/query.py` and `data/*.json` directly as fallback until B2 is built)
- **What to backfill:**

  | Gap | Target file | What to add |
  |-----|-------------|-------------|
  | Go service infra (Piri: 121 items, Guppy: 19, Storoku: 135) | `infrastructure-decisions.md` | New sections: Piri infrastructure (DynamoDB, S3, SQS, Lambda, SQL), Guppy infrastructure (SQL tables), Storoku/Forge infrastructure (ECS, RDS, Redis, S3) |
  | SQL schemas (57 tables, 0% covered) | `infrastructure-decisions.md` | Key SQL table schemas for Piri (32 tables) and Guppy (15 tables) — at least the core tables with column definitions |
  | Service connection map (231 edges, 9% covered) | `shared-packages.md` | New section: service-to-service connections with mechanism, capability, production URLs/DIDs |
  | Downstream consumers (9 apps, 0% covered) | `shared-packages.md` | New section: external apps that break if client API changes, with specific break notes |
  | Capability registry completeness (102 names, ~91 mentioned) | `ucanto-framework.md` | Update capability catalog with all 102 names, add `with`/`nb` schema references |
  | Indexing-service infra (Redis, legacy DynamoDB) | `go-ecosystem.md` or `infrastructure-decisions.md` | Indexing-service infrastructure section |

- **Approach:** Use `python tools/query.py` and `data/*.json` to query for each gap (B2 MCP server deferred), then write narrative sections in the appropriate memory files. The structured data provides the facts; the memory files provide the explanation of *why* things are structured this way.
- **Note:** This is complementary to B2, not redundant. MCP answers "what infra does Piri use?" (structured lookup). Memory files answer "why does Piri use DynamoDB for metadata but SQLite for blob indexes?" (rationale and patterns). Both are needed.
- **Validation:** After backfill, re-run the coverage analysis. Target: service graph coverage 9% → 60%+, Go service infra 0% → 80%+, SQL schemas 0% → 70%+.

### Phase B: Tooling Modernization (Medium Effort)

#### B1. Migrate slash commands to skills
- **Status:** `done`
- **What:** Convert `.claude/commands/{trace,impact,spec,new-capability}.md` to `.claude/skills/*/SKILL.md` format with YAML frontmatter
- **Why:** Skills support auto-trigger detection, richer metadata, resource files. Still git-committable and team-shareable.
- **Effort:** Medium (4 commands → 4 skills, test each)
- **Files:** `.claude/skills/*/SKILL.md` (create), `.claude/commands/*.md` (remove after migration)
- **Note:** Both commands and skills are committed to git and available to all team members

#### B2. Build MCP server for structured codebase knowledge
- **Status:** `deferred`
- **Deferred reason:** Scanners require local repo clones (579MB). Not practical for new team members. Rewriting scanners to use GitHub API is the right fix, but not the priority now. Current workaround: scanner JSON data is committed to `data/`, so the query tool works out of the box without repos.
- **What:** Build a stateless MCP server that gives any developer cross-repo knowledge about the entire Storacha organization — capabilities, dependencies, infrastructure, service graph — without needing to clone all 82 repos locally.
- **Why:** Analysis (9th research stream) revealed massive gaps between scanner data and memory files:
  - Service graph: 231 edges, only ~20 described narratively in memory (9% coverage)
  - Go service infrastructure: 275+ items at 0% coverage (Piri, Guppy, Storoku entirely missing)
  - SQL schemas: 57 tables at 0% coverage
  - Capability schemas: 175 entries, only ~40 detailed in memory (23%)
  - Downstream consumers: 9 apps at 0% coverage

  Research confirms MCP is the right delivery mechanism:
  - Pre-computed deterministic graphs: 15/15 correctness vs 6/15 for vector-only (arXiv 2601.08773)
  - Nx shipped exactly this pattern for their monorepo (MCP server exposing project graph)
  - Claude Code Tool Search (Jan 2026) loads tools on-demand — near-zero token overhead

- **Effort:** Medium (MCP server + scanner integration + configuration)
- **Files:** `tools/mcp-server/` (create), `.claude/settings.json` (configure)
- **Depends on:** None (can start any time, independent of other items)

**The developer experience problem:**

A developer works on `upload-service` — that's the only repo they have cloned. They ask: "What capabilities does indexing-service handle?" or "What infrastructure does Piri use?" Without all repos local, grep/glob can't answer this. The MCP server can.

**Architecture: stateless, scans via GitHub API**

```
┌─ Developer Setup ────────────────────────────────────────┐
│                                                           │
│  1. Clone storacha-analysis (this repo)                   │
│  2. npm install in tools/mcp-server/                      │
│  3. Configure in their .claude/settings.json              │
│     (or the repo's .claude/settings.json if shared)       │
│                                                           │
│  Done. MCP server starts when Claude Code starts.         │
└───────────────────────────────────────────────────────────┘

┌─ How the MCP Server Gets Data ───────────────────────────┐
│                                                           │
│  Two modes (automatic fallback):                          │
│                                                           │
│  MODE 1: Committed snapshot (instant, default)            │
│    data/api-surface-map.json  ─┐                          │
│    data/infrastructure-map.json├→ loaded into memory       │
│    data/product-map.json      ─┘  at startup (<100ms)     │
│                                                           │
│  MODE 2: Live scan via GitHub API (fresh, on-demand)      │
│    GitHub API (org: storacha) ──→ fetch package.json,      │
│    go.mod, wrangler.toml, sst.config, *.tf, etc.          │
│    from each repo's default branch                        │
│    ──→ builds same data structures in memory               │
│                                                           │
│  Fallback: starts with committed snapshot immediately.    │
│  If `--refresh` flag or `refresh_data` tool is called,    │
│  scans via GitHub API and updates the committed JSONs.    │
└───────────────────────────────────────────────────────────┘
```

**Why two modes:**
- **Snapshot mode** (default): Developer clones this repo, starts MCP server, data is there instantly. No GitHub token needed. Data is as fresh as the last CI run.
- **Live scan mode** (on-demand): Developer calls the `refresh_data` tool or runs with `--refresh`. MCP server uses GitHub API to scan all repos in the `storacha` org. Needs a `GITHUB_TOKEN`. Updates the committed JSON files so the next developer gets fresh data too.
- **CI keeps snapshots fresh**: D3's weekly pipeline re-runs scanners via GitHub API, commits updated JSONs. Developers always have reasonably fresh data without doing anything.

**No local clones needed.** The scanners are rewritten (or wrapped) to work via GitHub API: fetch `package.json`, `go.mod`, `wrangler.toml`, `sst.config.ts`, `*.tf`, capability definition files, etc. from each repo's default branch. This is the same data the current Python scanners extract from local clones, but fetched remotely.

**Stateless design:**
- No database, no SQLite, no persistent state
- JSON snapshot files committed to git (human-readable, diffable in PRs)
- MCP server builds in-memory indexes (Maps/Sets) at startup
- All queries are pure lookups against in-memory data
- Server restart = clean reload from JSON files

**In-memory data model (built at startup):**

```typescript
// Loaded from data/api-surface-map.json
const capabilityIndex = new Map<string, Capability>();        // name → full definition
const capsByRepo = new Map<string, Capability[]>();           // repo → capabilities
const serviceGraph = new Map<string, Edge[]>();               // service → outgoing edges
const reverseGraph = new Map<string, Edge[]>();               // service → incoming edges

// Loaded from data/infrastructure-map.json
const infraByRepo = new Map<string, InfraItem[]>();           // repo → infra items
const infraByType = new Map<string, InfraItem[]>();           // type → items across repos

// Loaded from data/product-map.json
const repoIndex = new Map<string, Repo>();                    // name → repo details
const productIndex = new Map<string, Product>();              // name → product details
const downstreamConsumers = new Map<string, Consumer>();      // name → break notes
```

**MCP tools to expose (11 tools):**

| # | Tool | Input | Returns |
|---|------|-------|---------|
| 1 | `lookup_capability` | capability name (e.g. `blob/add`) | Handler file, service, route, schema (`with`/`nb`), all repos that invoke it |
| 2 | `list_capabilities` | service or repo name | All capabilities defined, handled, and invoked by that service |
| 3 | `blast_radius` | package or capability name | Affected repos, risk tier, downstream consumers, break notes |
| 4 | `query_infrastructure` | service name | All DynamoDB tables, S3 buckets, SQS queues, SQL tables for that service |
| 5 | `service_connections` | service name | All edges from/to, mechanism, capability, env vars, production URLs |
| 6 | `repo_info` | repo name | Role, language, product, deps, capabilities, infra summary |
| 7 | `find_by_infra` | infra type (e.g. `dynamodb`, `sqs`) | All services using that infra type + resource names |
| 8 | `product_info` | product name | All repos in that product, roles, deps, downstream consumers |
| 9 | `capability_naming` | domain prefix (e.g. `blob/`, `space/`) | All existing capabilities in that namespace — for naming consistency |
| 10 | `sql_schema` | repo or table name | Full column definitions for SQL tables |
| 11 | `refresh_data` | — (optional: specific repo) | Re-scans org via GitHub API, updates snapshot. Returns summary of changes. |

**Implementation approach:**
1. **`tools/mcp-server/server.ts`** — TypeScript MCP server using `@modelcontextprotocol/sdk`. On startup: loads committed JSON snapshots, builds in-memory indexes. Each query tool is a lookup against Maps, returning markdown-formatted results.
2. **`tools/mcp-server/scanner.ts`** — GitHub API scanner module. Uses `@octokit/rest` to fetch file contents from repos in the `storacha` org. Extracts: package.json deps, go.mod deps, capability definitions (grep for `capability()`), wrangler/SST config, Terraform resources, SQL schemas. Produces the same JSON structure as the Python scanners but without needing local clones.
3. **`data/*.json`** — Committed snapshot files. Updated by CI or by calling `refresh_data`. Human-readable, diffable in PRs.
4. **`.claude/settings.json`** — Configure the MCP server with `stdio` transport. Can be committed to individual repos' `.claude/settings.json` so any developer working in a Storacha repo gets the MCP server automatically.
5. Tool names use Storacha domain vocabulary (`blast_radius`, `lookup_capability`) so Claude's Tool Search matches them.
6. Tool descriptions concise (<100 words each, ~50-70 tokens).

**Developer setup (one-time):**
```bash
# Option A: Reference this repo's MCP server from any Storacha repo
# In the target repo's .claude/settings.json:
{
  "mcpServers": {
    "storacha-knowledge": {
      "command": "npx",
      "args": ["tsx", "/path/to/storacha-analysis/tools/mcp-server/server.ts"]
    }
  }
}

# Option B: If storacha-analysis is published as an npm package:
{
  "mcpServers": {
    "storacha-knowledge": {
      "command": "npx",
      "args": ["@storacha/codebase-knowledge"]
    }
  }
}
```

**Token budget analysis:**
- 11 tools × ~700 tokens per definition = ~7,700 tokens upfront
- With Tool Search enabled (default): near-zero until actually invoked
- vs. bash approach: `python tools/query.py` output + JSON parsing in-context = 2,000-10,000 tokens per query
- Net savings: significant, especially for multi-query sessions

**Validation:**
```bash
# Test with committed snapshot data
claude mcp list                                    # Server appears with 11 tools
claude mcp call lookup_capability blob/add         # Returns handler, schema
claude mcp call blast_radius @ucanto/core           # Returns 15+ repos, extreme risk
claude mcp call query_infrastructure piri           # Returns DynamoDB, S3, SQS, SQL
claude mcp call service_connections freeway         # Returns all edges + URLs
claude mcp call capability_naming "blob/"           # Returns all blob/* capabilities

# Test live refresh (needs GITHUB_TOKEN)
export GITHUB_TOKEN=ghp_...
claude mcp call refresh_data                       # Scans org, updates data/*.json
```
Each query should return concise, markdown-formatted results under 500 tokens.

#### B3. Unified development workflow (Lean PRD + SDD + TDD)
- **Status:** `done`

The core process innovation: combining value-first conversational planning (lean PRD), spec-driven execution (SDD), and test-driven development (TDD) into a single workflow. The AI helps developers think about value, writes tests as verifiable targets, then writes implementation that passes those tests.

**Why TDD is central, not optional:**
- Anthropic calls test-first "the single highest-leverage thing you can do" with Claude Code
- Tests-as-prompts: 95.2% pass@1 (WebApp1K benchmark, May 2025)
- TDFlow: 94.3% resolution rate on SWE-bench Verified with TDD workflow (Oct 2025)
- Classic TDD reduces defect density 40-90% (Nagappan, Microsoft/IBM)
- AI code has 1.7x more issues than human code (Qodo 2025) — TDD is the antidote
- Kent Beck: TDD is a "superpower" that constrains the AI "unpredictable genie"
- The developer reviews TESTS (the intent) not just CODE (the implementation) — faster, more precise review

**The unified flow:**

```
Developer: "I want to build X"
         |
         v
┌─ TIER 0: TRIVIAL ──────────────────────────────────────────────┐
│  (typo fix, config change, one-line fix)                        │
│  Dev says "just do it" → AI implements + shows diff. Done.      │
└─────────────────────────────────────────────────────────────────┘
         |  (if non-trivial)
         v
┌─ PHASE 1: SPECIFY (Conversational, value-first) ──────────────┐
│                                                                 │
│  AI auto-detects complexity tier:                               │
│    Tier 1 (Quick, 2-3 min): bug fix, small change              │
│    Tier 2 (Standard, 5-10 min): new feature                    │
│    Tier 3 (Full, 15-25 min): architectural change              │
│                                                                 │
│  Value questions (all tiers):                                   │
│    1. What problem does this solve?                             │
│    2. Who benefits?                                             │
│    3. What does success look like?                              │
│    4. What's the time appetite?                                 │
│                                                                 │
│  Scope questions (Tier 2+):                                     │
│    5. What's the simplest version?                              │
│    6. What should we NOT build?                                 │
│    7. Known rabbit holes or risks?                              │
│    8. Existing patterns to follow? (AI checks codebase)         │
│                                                                 │
│  → Output: Feature Brief with testable acceptance criteria      │
└─────────────────────────────────────────────────────────────────┘
         |
         v  (Tier 1 skips to Decompose)
┌─ PHASE 2: DESIGN (Plan mode, no code yet) ─────────────────────┐
│                                                                 │
│  AI reads feature brief + explores codebase (read-only)         │
│  Produces: approach, files to change, interfaces, data flow,    │
│  test infrastructure needs, mocking patterns                    │
│  Developer reviews before any code                              │
│                                                                 │
│  → Output: Design notes (Tier 3: separate design.md)            │
└─────────────────────────────────────────────────────────────────┘
         |
         v
┌─ PHASE 3: DECOMPOSE + WRITE ACCEPTANCE TESTS ─────────────────┐
│                                                                 │
│  3a. AI breaks plan into ordered tasks:                         │
│    - 1-2 files per task, completable in <4 hours                │
│    - Independent tasks marked [P] for parallel execution        │
│    - Dependencies explicit when they exist                      │
│                                                                 │
│  3b. AI generates ACCEPTANCE TESTS from feature brief:          │
│    - Tests define "done" — the verifiable target for each task  │
│    - Written BEFORE any implementation (no context pollution)   │
│    - Follow existing test patterns (from per-repo CLAUDE.md)    │
│                                                                 │
│  3c. DEVELOPER REVIEWS TESTS + TASK LIST                        │
│    → Key review moment: reviewing tests (intent) is faster      │
│      and more precise than reviewing code (implementation)      │
│    → Catches requirement misunderstandings before any code      │
│                                                                 │
│  RULE: If a task reveals unexpected complexity,                 │
│  STOP and re-decompose before proceeding.                       │
│                                                                 │
│  → Output: Task list + acceptance test files (all RED/failing)  │
└─────────────────────────────────────────────────────────────────┘
         |
         v
┌─ PHASE 4: IMPLEMENT (TDD red-green-refactor per task) ────────┐
│                                                                 │
│  For each task:                                                 │
│    1. AI reads the pre-written acceptance test         (RED)    │
│    2. AI writes unit tests for specific approach       (RED)    │
│    3. AI implements minimal code to pass all tests     (GREEN)  │
│    4. AI refactors while keeping tests green           (REFACTOR)│
│    5. AI self-audits: "Compare implementation against           │
│       feature brief. List unaddressed requirements."            │
│    6. Run full test suite + lint + type-check                   │
│    7. Developer reviews diff                                    │
│    8. Mark task complete, move to next                          │
│                                                                 │
│  TDD GUARDS (enforced via rules):                               │
│    ✗ "NEVER delete, comment out, or weaken existing tests"      │
│    ✗ "Test BEHAVIOR, not implementation details"                │
│    ✗ "One test at a time. Single clear assertion per test."     │
│                                                                 │
│  Autonomy spectrum:                                             │
│    High: peripheral features, routine (auto-accept mode)        │
│    Medium: production features (task-by-task review)            │
│    Low: security, shared packages (interactive guidance)        │
└─────────────────────────────────────────────────────────────────┘
```

**Why this specific TDD integration (Hybrid — Option D from research):**
- Acceptance tests in Phase 3 → written WITHOUT implementation knowledge → no context pollution
- Unit tests per-task in Phase 4 → written WITH implementation context → right granularity
- Matches GitHub Spec Kit's enforced ordering: contract → integration → unit → source
- TDFlow achieved 94.3% on SWE-bench with pre-existing tests as targets
- alexop.dev: context isolation between test-writing and implementation is essential
- Developer review shifts from "is this code correct?" to "do these tests capture my intent?" — faster

**Master deliverables list:**

| # | Deliverable | Path | Purpose |
|---|-------------|------|---------|
| 1 | `/plan` skill | `.claude/skills/plan/SKILL.md` | Entry point: tier detection, value questions, feature brief generation, phase orchestration |
| 2 | Feature brief template | `.specs/TEMPLATE-feature-brief.md` | Standardized output for Phase 1 (see template below) |
| 3 | Design doc template (Tier 3) | `.specs/TEMPLATE-design-doc.md` | Adds: design notes, test infrastructure, migration strategy, rollback plan |
| 4 | TDD rules | `.claude/rules/tdd.md` | Always-loaded TDD enforcement (see B3-E Layer 1 for full content) |
| 5 | Workflow rules | `.claude/rules/development-workflow.md` | Always-loaded phase/dependency/review enforcement (see B3-E Layer 1) |
| 6 | Phase-gate hook | `.claude/hooks/phase-gate.sh` | Blocks file writes that violate current phase (see B3-E Layer 2) |
| 7 | TDD-guard hook | `.claude/hooks/tdd-guard.sh` | Blocks impl files if no test snapshot exists (see B3-E Layer 2) |
| 8 | Test-modification detector | `.claude/hooks/test-mod-detector.sh` | Flags test weakening during implement phase (see B3-E Layer 2) |
| 9 | Workflow-nudge hook | `.claude/hooks/workflow-nudge.sh` | Injects phase context, suggests /plan for feature requests (see B3-E Layer 2) |
| 10 | Red-test verification hook | `.claude/settings.json` (Stop hook) | Verifies acceptance tests fail before Phase 4 (see B3-E Layer 2) |
| 11 | Pre-commit: test pairing | `.husky/pre-commit` or `.git/hooks/pre-commit` | Rejects new source files without corresponding test (see B3-E Layer 3) |
| 12 | Pre-commit: spec warning | `.husky/pre-commit` or `.git/hooks/pre-commit` | Warns when >5 files changed with no active spec (see B3-E Layer 3) |
| 13 | Hook settings | `.claude/settings.json` | Wires all hooks together |
| 14 | `.specs/` directory structure | `.specs/active/`, `.specs/done/`, `.specs/TEMPLATE-*` | Filesystem state machine for phase tracking |

**Feature brief template** (`.specs/TEMPLATE-feature-brief.md`):
```markdown
# [Feature Name]
## Problem
[1-3 sentences: what's broken/missing, for whom]
## Success
[1 sentence: measurable outcome]
## Appetite
[Time budget: "2 days" / "1 week" / "2 weeks"]
## Solution
[2-5 sentences: approach, referencing existing patterns]
## No-gos
- [Thing we will NOT build]
## Acceptance Criteria
- [ ] [Testable criterion — becomes an acceptance test]
## Tasks
- [ ] [Concrete task] → test: `test/feature/task-1.test.ts`
- [ ] Task 3 (after: 1, 2) → test: `test/feature/task-3.test.ts`
- [P] [Independent task] → test: `test/feature/task-2.test.ts`
## Risks
- [Known rabbit hole]
```

**Key design decisions (from 8 research streams):**

*From lean PRD research:*
- Conversational, not form-filling. Value-first, always. 5-15 min max.
- No story points, no mandatory GIVEN/WHEN/THEN. One person approves.
- AI skips obvious questions. Codebase-aware questioning.

*From SDD research:*
- Specify → Design → Decompose → Implement (Kiro/spec-kit consensus)
- "Spec-first" level (not spec-anchored or spec-as-source)
- Feature briefs are execution context, not forgotten docs

*From TDD research:*
- Tests-as-spec is the strongest pattern (95.2% pass@1)
- Acceptance tests before implementation (context isolation)
- Unit tests during implementation (right granularity)
- Self-audit after each task (Addy Osmani recommendation)
- Guard rails against test deletion (Kent Beck's documented experience)

*From workflow benchmarking:*
- 3-tier complexity is a genuine innovation (Fowler critique of Kiro validates need)
- Value-first questioning is unique among all AI coding tools
- Tier 0 escape hatch prevents over-specification (Marmelab critique)
- Parallel task markers [P] future-proof for multi-agent (spec-kit pattern)
- Self-audit instruction catches drift early (Osmani)
- Spec persistence model (active → done) prevents spec rot (Thoughtworks warning)

*From enforcement research:*
- Prompt-only rules degrade to 42-53% compliance at scale (IFScale)
- 3-layer defense-in-depth: rules → hooks → CI (each catches what the previous misses)
- Hooks are deterministic — the only reliable enforcement for critical rules
- Subagent isolation raises TDD compliance from ~20% to ~84% (alexop.dev)
- Filesystem state machine (PHASE file) enables hook-based phase gating
- Hook escape procedures are critical for adoption (blocked devs remove all hooks)

**Research backing (key data points):**

| Finding | Data | Source |
|---------|------|--------|
| Test-first = highest leverage for Claude Code | Official recommendation | Anthropic engineering blog |
| Tests-as-prompts pass rate | 95.2% pass@1 | WebApp1K (May 2025) |
| TDD workflow resolution rate | 94.3% on SWE-bench | TDFlow (Oct 2025) |
| TDD defect density reduction | 40-90% | Nagappan (Microsoft/IBM) |
| AI code issue rate vs human | 1.7x more issues | Qodo 2025 |
| Experienced devs slower without structure | 19% slower | METR study (Jul 2025) |
| Requirement traceability with specs | +40% | EPAM spec-kit study |
| Defect costs originating in requirements | 64% | iSixSigma |
| Test hacking rate with proper TDD workflow | 0.875% (7/800) | TDFlow |
| Property-based + example-based detection | 81.25% | Arxiv 2510.09907 |

**TDD anti-patterns to guard against:**

| Anti-Pattern | Risk | Mitigation |
|---|---|---|
| Test deletion | AI deletes failing tests instead of fixing code | Rules: "NEVER delete tests" + file-watch hooks |
| Context pollution | Implementation knowledge bleeds into test logic | Write acceptance tests in Phase 3 (before impl) |
| Teaching to the test | Code passes tests but doesn't implement intent | Human reviews tests in Phase 3; behavioral tests |
| Over-testing | AI generates trivial tests for implementation details | Rules: "Test behavior, not implementation" |
| Brittle tests | Tests coupled to implementation, break on refactor | Rules: "Test public API, not internals" |

---

### B3-E. Enforcement Architecture

The workflow above describes *what should happen*. This section describes *how we make it stick*. Research (8th stream: enforcement mechanisms, 30+ sources) shows prompt-only enforcement degrades to 42-53% compliance at scale (IFScale, Jaroslawicz 2025). We use a 3-layer defense-in-depth model.

**The enforcement principle:**
> "If you tell Claude Code in your CLAUDE.md not to modify .env files, it will *probably* listen.
> If you set up a PreToolUse hook that blocks writes to .env files, it will *always* block them."
> — Anthropic docs

**Full research report:** `research/enforcement-mechanisms.md`

#### Layer 1: Rules (Guidelines, ~60-80% compliance)

`.claude/rules/` files — always loaded, imperative, short. These are the first line of defense. They catch most violations through prompt compliance, but cannot guarantee enforcement under pressure.

**Rule file: `.claude/rules/tdd.md`**
```markdown
# TDD Rules (Non-Negotiable)

- Write failing tests BEFORE implementation code. No exceptions.
- NEVER delete, comment out, skip, or weaken an existing test.
- "Weaken" means: changing exact assertions to range assertions, reducing assertion count,
  changing `toBe` to `toBeDefined`, adding `.skip`/`.todo`, wrapping in conditionals,
  or changing expected error types to generic errors.
- If a test seems wrong, FLAG IT for developer review. Do not change it yourself.
- Test BEHAVIOR (observable output for given input), not implementation details.
- Test the public API, not internal functions.
- One test at a time: write one failing test → implement → green → next test.
- After completing a task, self-audit: re-read the feature brief and list any
  unaddressed acceptance criteria. If any in-scope criteria are unaddressed,
  go back and add tests + implementation before proceeding.
```

**Rule file: `.claude/rules/development-workflow.md`**
```markdown
# Development Workflow Rules

## Phase Ordering (Mandatory)
You MUST follow this sequence. NEVER skip a phase.
1. SPECIFY: Ask value questions, produce feature brief. No code, no design.
2. DESIGN: Explore codebase read-only, produce design notes. No code, no tests.
3. DECOMPOSE + TEST: Break into tasks, write acceptance tests. Tests MUST fail.
4. IMPLEMENT: One task at a time, TDD red-green-refactor.

## Phase Constraints
- Phase 1-2: PLAN MODE ONLY. Do NOT create .ts/.js/.go/.py source files.
- Phase 3: You may ONLY create/modify test files (*test*, *spec*, *_test.go).
- Phase 4: Implement ONE task at a time. Do NOT start a blocked task.

## Before Each Task (Phase 4)
Re-read the task description from the feature brief AND the acceptance test.
Quote the acceptance criteria you are implementing. This prevents spec drift.

## Tier 0 Sanity Check
Even if the developer says "just do it," escalate to Tier 1 if the change:
- Touches more than 3 files
- Modifies a package in the blast radius table (CLAUDE.md)
- Changes a capability schema or shared interface
- Touches test infrastructure or CI config
Say: "This looks bigger than trivial because [reason]. Quick planning flow?"

## Stop-and-Redecompose Triggers
STOP implementation and re-decompose if:
- A task requires changing more than the planned 1-2 files
- You discover an undocumented dependency between tasks
- You need to modify a high-blast-radius package not in the plan
- A test reveals the Phase 2 interface design won't work
- You've attempted 3+ approaches for the same test failure
STOP means: do NOT commit in-progress changes. Report to the developer:
"Unexpected complexity: [description]. Current tasks need revision."

## Dependency Enforcement
Tasks use explicit dependency notation:
  - `[ ] Task 3 (after: 1, 2)` — blocked by tasks 1 and 2
  - `[P] Task 4` — independent, can run in any order
Before starting a task, verify ALL predecessor tasks are complete.
If predecessors are incomplete, work on an unblocked task instead.

## Mandatory Review Gates
Use AskUserQuestion to pause at EVERY phase transition:
- After Phase 1: "Here's the feature brief. Approve before I design?"
- After Phase 2: "Here's the design. Approve before I write tests?"
- After Phase 3: "Here are the tests (all failing). Approve before I implement?"
These gates are mandatory even in high-autonomy mode.

## Spec Persistence
- Create `.specs/active/{feature-slug}/` at Phase 1 start
- Write brief.md, design.md, tasks.md as phases complete
- Move to `.specs/done/{feature-slug}/` after merge
```

#### Layer 2: Hooks (Guardrails, ~90%+ compliance)

Deterministic enforcement via `.claude/settings.json`. Hooks fire on every tool call and cannot be bypassed by the AI. This is where the critical gates live.

**Hook: Phase gate (PreToolUse — blocks writes that violate current phase)**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [{
          "type": "command",
          "command": "bash .claude/hooks/phase-gate.sh"
        }]
      }
    ]
  }
}
```

`.claude/hooks/phase-gate.sh`:
```bash
#!/bin/bash
# Reads current phase from .specs/active/*/PHASE
# Blocks file writes that don't match the current phase
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

# Find active spec phase (if any)
# NOTE: Only one active spec at a time. Multiple concurrent specs not supported.
PHASE_FILES=($(ls .specs/active/*/PHASE 2>/dev/null))
if [ ${#PHASE_FILES[@]} -eq 0 ]; then
  exit 0  # No active workflow — no restrictions
fi
if [ ${#PHASE_FILES[@]} -gt 1 ]; then
  echo "BLOCKED: Multiple active specs found. Complete or archive one first." >&2
  exit 2
fi
PHASE_FILE="${PHASE_FILES[0]}"
PHASE=$(cat "$PHASE_FILE")

IS_TEST=0
[[ "$FILE_PATH" =~ (test|spec|_test\.go) ]] && IS_TEST=1

IS_SOURCE=0
[[ "$FILE_PATH" =~ \.(ts|js|go|py)$ ]] && [[ $IS_TEST -eq 0 ]] && IS_SOURCE=1

case "$PHASE" in
  specify|design)
    if [ $IS_SOURCE -eq 1 ] || [ $IS_TEST -eq 1 ]; then
      echo "BLOCKED: Phase is '$PHASE'. No source or test files allowed yet." >&2
      exit 2
    fi
    ;;
  decompose)
    if [ $IS_SOURCE -eq 1 ]; then
      echo "BLOCKED: Phase is 'decompose'. Only test files allowed, not source files." >&2
      exit 2
    fi
    ;;
  implement)
    # All files allowed in implement phase
    ;;
esac
exit 0
```

**Hook: TDD guard (PreToolUse — blocks impl files if no failing tests exist)**
```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "bash .claude/hooks/tdd-guard.sh"
      }]
    }
  ]
}
```

`.claude/hooks/tdd-guard.sh`:
```bash
#!/bin/bash
# During implement phase: block source file creation if no test files exist
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

PHASE_FILE=$(ls .specs/active/*/PHASE 2>/dev/null | head -1)
[ -z "$PHASE_FILE" ] && exit 0
PHASE=$(cat "$PHASE_FILE")
[ "$PHASE" != "implement" ] && exit 0

# Only check source files, not tests/specs/configs
IS_SOURCE=0
[[ "$FILE_PATH" =~ \.(ts|js|go|py)$ ]] && IS_SOURCE=1
[[ "$FILE_PATH" =~ (test|spec|_test\.go) ]] && IS_SOURCE=0
[ $IS_SOURCE -eq 0 ] && exit 0

# Check that at least one test file exists in the active spec
SPEC_DIR=$(dirname "$PHASE_FILE")
TESTS_DIR="$SPEC_DIR/tests-snapshot"
if [ ! -d "$TESTS_DIR" ] || [ -z "$(ls -A "$TESTS_DIR" 2>/dev/null)" ]; then
  echo "BLOCKED: No test snapshot found. Write and run acceptance tests first (Phase 3)." >&2
  exit 2
fi
exit 0
```

**Hook: Test modification detector (PreToolUse — flags test file changes during implement)**

Uses a bash pre-filter to avoid spawning an agent on every file write. Only invokes the agent when a test file is being modified during implement phase.

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "bash .claude/hooks/test-mod-detector.sh"
      }]
    }
  ]
}
```

`.claude/hooks/test-mod-detector.sh`:
```bash
#!/bin/bash
# Pre-filter: only flag test file modifications during implement phase
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

# Quick exits for non-test files or non-implement phases
PHASE_FILE=$(ls .specs/active/*/PHASE 2>/dev/null | head -1)
[ -z "$PHASE_FILE" ] && exit 0
PHASE=$(cat "$PHASE_FILE")
[ "$PHASE" != "implement" ] && exit 0

IS_TEST=0
[[ "$FILE_PATH" =~ (test|spec|_test\.go) ]] && IS_TEST=1
[ $IS_TEST -eq 0 ] && exit 0

# This IS a test file modification during implement phase.
# Check if the test exists in the snapshot (pre-existing test being modified)
SPEC_DIR=$(dirname "$PHASE_FILE")
BASENAME=$(basename "$FILE_PATH")
if [ -f "$SPEC_DIR/tests-snapshot/$BASENAME" ]; then
  # Pre-existing acceptance test being modified — flag for developer review
  echo "WARNING: Modifying acceptance test '$BASENAME' during implementation." >&2
  echo "If the test is wrong, get developer approval. If the code is wrong, fix the code." >&2
  # Exit 0 (allow) but with warning. For strict mode, change to exit 2 (block).
fi
exit 0
```

> **Design note:** The bash pre-filter handles 95%+ of writes (non-test files) instantly. For stricter enforcement, change the final `exit 0` to `exit 2` to hard-block all acceptance test modifications during implement. The agent-based approach (spawning a sub-agent to diff against snapshot) is available as an upgrade but adds ~5s latency per test-file write.

**Hook: Workflow activation (UserPromptSubmit — suggests /plan for feature requests)**
```json
{
  "UserPromptSubmit": [
    {
      "hooks": [{
        "type": "command",
        "command": "bash .claude/hooks/workflow-nudge.sh"
      }]
    }
  ]
}
```

`.claude/hooks/workflow-nudge.sh`:
```bash
#!/bin/bash
# If no active spec exists and the message looks like a feature request,
# inject a reminder to use /plan
ACTIVE=$(ls .specs/active/*/PHASE 2>/dev/null | head -1)
if [ -z "$ACTIVE" ]; then
  echo '{"additionalContext": "No active workflow detected. If this is a non-trivial feature request, suggest using /plan to structure the work."}'
else
  PHASE=$(cat "$ACTIVE")
  FEATURE=$(basename "$(dirname "$ACTIVE")")
  echo "{\"additionalContext\": \"Active workflow: $FEATURE (phase: $PHASE). Stay within phase constraints.\"}"
fi
```

**Hook: Red-test verification (Stop — after Phase 3, verify tests fail)**
```json
{
  "Stop": [
    {
      "hooks": [{
        "type": "agent",
        "prompt": "Check if .specs/active/*/PHASE says 'decompose' and test files were just created. If so: (1) identify all new test files, (2) run them (npm test or go test as appropriate), (3) verify they ALL fail. If any test passes, respond: {\"decision\": \"block\", \"reason\": \"Acceptance test [name] already passes. Either the feature exists or the test is vacuous. Investigate before moving to implement phase.\"}",
        "timeout": 60
      }]
    }
  ]
}
```

#### Layer 3: CI / Pre-commit (Hard Gates, ~100%)

Last line of defense. Cannot be bypassed.

**Pre-commit hook: test-file pairing**
```bash
#!/bin/bash
# Reject commits where new source files have no corresponding test file
for f in $(git diff --cached --name-only --diff-filter=A); do
  if [[ "$f" =~ \.(ts|js)$ ]] && [[ ! "$f" =~ (test|spec|\.d\.ts) ]]; then
    test_file="${f/.ts/.test.ts}"
    alt_test="${f/.js/.test.js}"
    if ! git diff --cached --name-only | grep -qE "(${test_file}|${alt_test})"; then
      echo "ERROR: New source file $f has no corresponding test." >&2
      exit 1
    fi
  fi
done
```

**Pre-commit hook: spec exists for non-trivial changes**
```bash
#!/bin/bash
# If more than 5 files changed and no active spec, warn
FILE_COUNT=$(git diff --cached --name-only | wc -l)
ACTIVE=$(ls .specs/active/*/PHASE 2>/dev/null | head -1)
if [ "$FILE_COUNT" -gt 5 ] && [ -z "$ACTIVE" ]; then
  echo "WARNING: $FILE_COUNT files changed with no active spec. Consider using /plan." >&2
  # Warning only, not blocking — developer decides
fi
```

#### Subagent Isolation (Context Pollution Prevention)

The single-agent architecture means test-writing (Phase 3) and implementation (Phase 4) share context. Research shows this degrades TDD quality (alexop.dev: compliance jumped from 20% to 84% with isolation).

**Mitigation strategy:**
1. **Phase 3 test-writing uses a subagent** (Task tool with `subagent_type: general-purpose`). The subagent receives ONLY the feature brief and acceptance criteria — no codebase exploration results from Phase 2. This prevents implementation ideas from leaking into test design.
2. **Phase 4 implementation starts with a context refresh.** The `/plan` skill explicitly re-reads the feature brief and test files at the start of Phase 4, pushing Phase 2 exploration results out of active attention.
3. **Test snapshot at Phase 3 exit.** All test files are copied to `.specs/active/{feature}/tests-snapshot/`. The test-modification-detector hook diffs against this snapshot during Phase 4.

#### Self-Audit Hardening

The Phase 4 step 5 self-audit is structurally unreliable (same model evaluating its own work). Mitigations:

1. **Structured output required.** Self-audit must produce a checklist, not free-form text:
   ```
   Acceptance Criteria Audit:
   - [ ] Criterion 1: [PASS/FAIL/PARTIAL] — evidence: test_name or file:line
   - [ ] Criterion 2: [PASS/FAIL/PARTIAL] — evidence: test_name or file:line
   ```

2. **Mechanical cross-check.** After self-audit, run: "For each acceptance criterion, grep the test files for a test that asserts on it. List any criteria with no matching test." This is a search task, not a judgment task — more reliable.

3. **Consequences defined.** If self-audit finds unaddressed in-scope criteria: go back to step 2 (write tests + implement). Do NOT proceed to step 6. Out-of-scope discoveries become follow-up tasks.

4. **Future: verifier subagent (D1).** When D1 is implemented, the self-audit step is replaced by a separate agent that diffs the feature brief against test coverage and implementation. This provides true independence.

#### Enforcement Summary

| Gap | Layer 1 (Rules) | Layer 2 (Hooks) | Layer 3 (CI) |
|-----|-----------------|-----------------|--------------|
| Phase skipping | "NEVER skip a phase" | Phase-gate hook blocks wrong file types | — |
| Test-before-code | "Write failing tests BEFORE implementation" | TDD-guard hook blocks source without tests | Pre-commit: test pairing |
| Test modification | "NEVER weaken tests" | Test-modification-detector agent hook | — |
| Spec drift | "Re-read brief before each task" | UserPromptSubmit injects phase context | — |
| Dependency violation | "Verify predecessors complete" | — (prompt-only, medium risk) | — |
| Tier 0 overuse | "Escalate if >3 files or blast radius" | Workflow-nudge hook | Spec-exists warning |
| Stop-and-redecompose | Explicit trigger criteria | — (prompt-only, medium risk) | — |
| Context pollution | — | Phase 3 in subagent; test snapshot | — |
| Review gate bypass | "Use AskUserQuestion at transitions" | — (prompt-only, medium risk) | — |
| Red-test verification | "Tests MUST fail" | Stop hook runs tests after Phase 3 | — |

**Known gaps with prompt-only enforcement (future hardening):**
- Dependency ordering: Could add a hook that reads tasks.md and blocks work on tasks with incomplete predecessors
- Review gates: Could add a Stop hook that checks for AskUserQuestion usage at phase boundaries
- Stop-and-redecompose: Could add a PostToolUse hook counting file modifications per task

#### Hook Escape Procedures

Hooks must never become a brick wall. If a developer gets blocked with no workaround, they'll remove all hooks. These escape procedures are documented and expected to be used occasionally.

**Temporary disable (per-session):**
```bash
# Disable all hooks for current session
export CLAUDE_HOOKS_DISABLED=1

# Or disable a specific hook by renaming
mv .claude/hooks/phase-gate.sh .claude/hooks/phase-gate.sh.disabled
# Re-enable when done
mv .claude/hooks/phase-gate.sh.disabled .claude/hooks/phase-gate.sh
```

**Reset stuck phase state:**
```bash
# If .specs/active/*/PHASE gets stuck or corrupted
echo "implement" > .specs/active/my-feature/PHASE   # Force to specific phase
# Or abandon the active spec entirely
rm -rf .specs/active/my-feature/                      # Remove active spec
```

**Emergency bypass for hot fixes:**
```bash
# Skip pre-commit hooks for urgent production fixes
git commit --no-verify -m "hotfix: ..."
```

**Rules of engagement:**
- Disabling hooks is fine for emergencies. Re-enable immediately after.
- If a hook blocks legitimate work more than twice for the same reason, the hook needs fixing — file an issue.
- `--no-verify` for hot fixes is acceptable but the fix should get proper tests in a follow-up PR.

---

**Effort:** Large (14 deliverables: skill + 2 templates + 2 rule files + 5 hooks + 2 pre-commit hooks + settings + directory structure)
**Files:** See master deliverables list above
**Depends on:** A4 (rules directory) — B3's rule files live in `.claude/rules/` which A4 creates. No dependency on B1 (B3 creates a new `/plan` skill, not a migration).

### Phase C: Coverage & Automation (Higher Effort)

#### C1. Auto-generate CLAUDE.md for uncovered repos
- **Status:** `done`
- **What:** Script that generates minimal CLAUDE.md from README + package.json/go.mod + CI config for the 61 repos without one
- **Why:** 61/82 repos have no guidance; even basic info (language, build command, test command, key abstractions) helps. Multi-repo score 7/10 — second-biggest gap after freshness.
- **Effort:** Medium (script + manual review of output)
- **Files:** `tools/generate-repo-claude-md.py` (create), `repos/storacha/*/CLAUDE.md` (generated)
- **Depends on:** None (can start any time, but benefits from A4 conventions being established)
- **Approach:**
  1. Script reads each repo's manifest (`package.json`, `go.mod`, `Cargo.toml`)
  2. Extracts: language, dependencies, build/test commands, entry points
  3. Reads `README.md` for project description and key concepts
  4. Reads CI config (`.github/workflows/`) for test/lint/build commands
  5. Generates a CLAUDE.md following the existing 21-repo template pattern:
     ```markdown
     # {repo-name}
     ## Overview
     [From README, 2-3 sentences]
     ## Quick Reference
     - **Language:** {lang} | **Build:** `{cmd}` | **Test:** `{cmd}` | **Lint:** `{cmd}`
     ## Key Abstractions
     [Top 5 exports/types from package manifest]
     ## Conventions
     [Inherited from parent — link to root CLAUDE.md]
     ```
  6. Human reviews each generated file before committing (batch of ~10 at a time)
- **Validation:** Run the script, manually review 5 generated files for accuracy, compare with the 21 hand-written CLAUDE.md files for consistency
- **Expected output:** ~61 new CLAUDE.md files, multi-repo coverage 21/82 → 82/82

#### C2. Add staleness validation script
- **Status:** `done`
- **What:** Script that compares memory file claims against scanner data and flags potential drift
- **Why:** Automates freshness checking; can be run on-demand or in CI. Freshness score 4/10 — critical gap. A1 adds dates but without automated checking, dates themselves go stale.
- **Effort:** Medium
- **Files:** `tools/validate-freshness.py` (create)
- **Depends on:** A1 (staleness headers must exist to parse)
- **Approach:**
  1. Parse all memory files for `<!-- Last validated: ... -->` headers
  2. Compare quantitative claims against `data/*.json` directly (B2 MCP server deferred; use `python tools/query.py` or read JSON):
     - Capability count, service edge count
     - DynamoDB table count, R2 bucket count
     - Repo count, package dependency counts
  3. Compare named references (specific middleware names, capability names, service names) against scanner data
  4. Flag files where:
     - Last validated date is >90 days old
     - Quantitative claims differ from scanner data by >10%
     - Named entities appear in memory but not in scanner (or vice versa)
  5. Output: markdown report with file:line references and suggested fixes
- **Deliverables:**
  - `tools/validate-freshness.py` — the validation script
  - `.claude/rules/freshness.md` — rule telling AI to run validation before relying on stale files
- **Validation:** Run against current memory files, verify it catches known inaccuracies. Should flag at least 5 genuine drift issues on first run.

#### C3. Add "Discover" skill for unknown repos
- **Status:** `done`
- **What:** A skill that guides systematic exploration of repos without CLAUDE.md: scan manifest, identify patterns, map abstractions, document test approach
- **Why:** D3 research: structured discovery ("Discover phase") is highest-value brownfield intervention. Even with C1's auto-generated CLAUDE.md files, a human-guided discovery pass produces deeper understanding.
- **Effort:** Small-medium
- **Files:** `.claude/skills/discover-repo/SKILL.md` (create)
- **Depends on:** B1 (skills infrastructure — needs skill format established)
- **Approach:**
  The `/discover` skill runs a structured exploration sequence:
  1. **Manifest scan:** Read package.json/go.mod, identify language, deps, scripts
  2. **Entry point mapping:** Find main exports, CLI entry points, HTTP handlers
  3. **Pattern recognition:** Match against known Storacha patterns:
     - ucanto server/client setup → service handler repo
     - Cloudflare Worker entry → edge service
     - SST infrastructure → infra-as-code repo
     - CLI with commander/yargs → developer tool
  4. **Test infrastructure:** Identify test framework, fixtures, test patterns
  5. **Dependency analysis:** Cross-reference against `shared-packages.md` blast radius
  6. **Output:** Draft CLAUDE.md (if none exists) or enhancement suggestions (if one exists)

  The skill uses `AskUserQuestion` to confirm findings and ask about undocumented conventions. Produces a structured report that can be committed as the repo's CLAUDE.md.
- **Validation:** Run `/discover` on 3 repos without CLAUDE.md. Verify output is accurate and useful. Compare quality against C1 auto-generated files.

### Phase D: Process Improvements (Ongoing)

#### D1. Add reviewer/verifier subagent
- **Status:** `done`
- **What:** A verification subagent that reviews proposed changes against conventions, blast radius rules, test requirements, and feature brief before the developer sees them
- **Why:** D3 framework dual-agent architecture improves brownfield output quality. Self-audit (B3-E) is unreliable because same model evaluates own work. An independent reviewer in a fresh context catches what self-audit misses.
- **Effort:** Medium
- **Files:** `.claude/skills/review/SKILL.md` (create), `.claude/rules/review-process.md` (create)
- **Depends on:** B3 (needs the workflow and spec structure to review against)
- **Approach:**
  The reviewer is a subagent (Task tool, `subagent_type: general-purpose`) invoked at two points:

  **Review point 1: After Phase 3 (test review)**
  Subagent receives: feature brief + acceptance test files. Fresh context, no implementation bias.
  Checks:
  - Every acceptance criterion has a corresponding test
  - Tests assert on behavior, not implementation details
  - Tests follow the repo's existing test patterns (from per-repo CLAUDE.md)
  - No overly-permissive assertions (`toBeDefined`, `toBeGreaterThan(0)`)

  **Review point 2: After Phase 4 per-task completion (code review)**
  Subagent receives: feature brief + test files + diff of changed files. Fresh context.
  Checks:
  - Changed files match the task plan (no scope creep)
  - No high-blast-radius packages modified without explicit plan mention
  - Code follows conventions from `.claude/rules/` (naming, imports, error handling)
  - No test files were weakened (diff against tests-snapshot)
  - All acceptance tests pass

  **Output format:**
  ```
  ## Review: Task {N} — {name}
  ### PASS / FAIL / NEEDS_ATTENTION
  - [x] Files match task plan
  - [x] Conventions followed
  - [ ] ATTENTION: Modified shared package @storacha/capabilities — not in plan
  - [x] Tests unchanged
  - [x] All tests pass
  ### Comments
  - Line 42 of upload-handler.ts: error handling uses throw instead of Result pattern
  ```

  Developer sees this review output before approving the task completion.
- **Validation:** Run reviewer on a completed B3 task. Intentionally introduce a convention violation and a test weakening — verify the reviewer catches both.

#### D2. Document subagent delegation patterns
- **Status:** `done`
- **What:** Add guidance to CLAUDE.md and rules on when to use subagents: unfamiliar repos, cross-service traces, blast radius investigations, Phase 3 test writing, Phase 4 review
- **Why:** 90.2% improvement on complex research tasks with multi-agent (Anthropic docs). Current CLAUDE.md has no guidance — developers don't know subagents exist or when to use them.
- **Effort:** Small
- **Files:** `CLAUDE.md` (edit), `.claude/rules/subagent-patterns.md` (create)
- **Depends on:** B3 (workflow establishes the subagent patterns), D1 (reviewer is a key subagent)
- **Approach:**
  Create `.claude/rules/subagent-patterns.md`:
  ```markdown
  # When to Use Subagents

  ## Always use a subagent for:
  - Phase 3 acceptance test writing (context isolation from Phase 2 design)
  - Phase 4 code review (D1 reviewer pattern — independent verification)
  - Cross-repo impact analysis (explore multiple repos without polluting main context)
  - Research tasks (web search, spec lookup — keep main context focused on code)

  ## Consider a subagent for:
  - Exploring an unfamiliar repo (use /discover skill via subagent)
  - Blast radius investigation (check all downstream consumers of a package)
  - Debugging complex failures (isolate investigation from fix attempts)

  ## Do NOT use a subagent for:
  - Simple file reads or searches (use Grep/Glob directly)
  - Single-file edits with clear instructions
  - Tasks requiring main conversation context (user preferences, prior decisions)

  ## Subagent hygiene:
  - Pass explicit context (file paths, feature brief content), not "see above"
  - Subagents start with fresh context — they can't see your conversation
  - Keep subagent prompts under 500 words — longer prompts hit instruction-following limits
  - Prefer `subagent_type: general-purpose` for tasks needing Write/Edit access
  - Prefer `subagent_type: Explore` for read-only research
  ```

  Update CLAUDE.md routing table with a "When to use subagents" entry pointing to this file.
- **Validation:** Verify the rules file loads correctly. Test that the AI suggests subagent use when encountering a cross-repo investigation.

#### D3. Set up CI pipeline for knowledge freshness
- **Status:** `done`
- **What:** GitHub Action that runs weekly: re-scans key repos, compares to scanner data, creates issue if drift detected
- **Why:** Automated staleness detection — currently manual. C2 provides the script; D3 automates it.
- **Effort:** Medium-large
- **Files:** `.github/workflows/knowledge-freshness.yml` (create), `tools/validate-freshness.py` (from C2)
- **Depends on:** C2 (validation script)
- **Approach:**
  1. GitHub Action runs on weekly schedule (Sunday night)
  2. Checks out the storacha-analysis repo
  3. Runs `python tools/validate-freshness.py --ci --output report.json`
  4. If drift detected (exit code 1):
     - Creates/updates a GitHub issue titled "Knowledge Freshness Report — Week of {date}"
     - Issue body contains the drift report in markdown
     - Labels: `knowledge-maintenance`, `automated`
  5. If no drift (exit code 0): no action
  6. Optional: re-run scanners against key repos (upload-service, w3up, freeway, indexing-service, piri) and compare output against cached scanner JSONs

  ```yaml
  # .github/workflows/knowledge-freshness.yml
  name: Knowledge Freshness Check
  on:
    schedule:
      - cron: '0 2 * * 0'  # Sunday 2am UTC
    workflow_dispatch: {}   # Manual trigger

  jobs:
    validate:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.12'
        - run: python tools/validate-freshness.py --ci --output report.json
        - name: Create issue on drift
          if: failure()
          uses: peter-evans/create-issue-from-file@v5
          with:
            title: 'Knowledge Freshness Report — ${{ github.event.schedule }}'
            content-filepath: report.json
            labels: knowledge-maintenance, automated
  ```
- **Validation:** Trigger manually via `workflow_dispatch`. Verify it produces accurate report. Intentionally introduce a stale claim and verify the issue gets created.

#### D4. Continuous improvement feedback loop
- **Status:** `done`
- **What:** A lightweight process for capturing what works and what doesn't in the B3 workflow, feeding improvements back into the rules and hooks
- **Why:** The workflow will need tuning. Without a feedback mechanism, pain points accumulate silently until developers abandon the workflow.
- **Effort:** Small
- **Files:** `.specs/RETRO-TEMPLATE.md` (create), MEMORY.md (update)
- **Depends on:** B3 (workflow must be in use)
- **Approach:**
  After every 5th feature completed through the B3 workflow, the `/plan` skill prompts:
  ```
  You've completed 5 features through the workflow. Quick retro:
  1. Which phase felt most valuable? Least valuable?
  2. Did any hook block you incorrectly? Which one?
  3. Did the tier selection feel right, or did you override it?
  4. What would make this faster?
  ```
  Responses are appended to `.specs/retro-log.md`. Patterns are reviewed monthly and fed back into rule/hook updates.

  Also: the `/plan` skill logs workflow telemetry to `.specs/telemetry.jsonl`:
  - Tier selected vs actual effort
  - Phases skipped (Tier 1 skipping Phase 2)
  - Hook blocks triggered (which hook, how resolved)
  - Time per phase (rough, from timestamps)

  This data drives future enforcement tuning. If a hook blocks legitimate work >20% of the time, it needs adjustment.
- **Validation:** Verify retro template generates useful output. Verify telemetry captures at least tier, phase, and hook-block events.

## Meta-Plan Dependency Graph

```
A1 (staleness headers)  ──────────────────────────────────→ C2 (freshness script)
A2 (spec references)                                             │
A3 (TL;DR summaries)                                             ├──→ D3 (CI pipeline)
A4 (rules directory)  ──→ B3 (unified workflow) ──→ D1 (reviewer subagent)
                          │                          │
                          │                          ├──→ D2 (subagent docs)
                          │                          │
                          │                          └──→ D4 (feedback loop)
                          │
B1 (commands→skills)  ──→ C3 (discover skill)
B2 (MCP server)  ──→ A5 (backfill scanner data into memory)
                  ──→ C2 (freshness script uses MCP/JSON as data source)

C1 (auto-gen CLAUDE.md)  — no hard deps, benefits from A4 conventions
```

**Two critical paths:**
1. A4 → B3 → D1 (rules directory → workflow → reviewer) — process path
2. ~~B2 → A5~~ (B2 deferred; A5 unblocked via query tool fallback) — knowledge path

**Parallelizable groups:**
- Group 1: A1 + A2 + A3 (all memory file enhancements, independent)
- Group 2: A4 + B1 (both create new infrastructure, independent of each other; B2 deferred)
- Group 3: B3 + A5 (B3 depends on A4, A5 unblocked — can run in parallel once Group 2 done)
- Group 4: C1 + C2 (both are scripts, C2 depends on A1)
- Group 5: D1 + D2 (both depend on B3 but are independent of each other)

**Item dependency summary:**

| Item | Hard depends on | Soft depends on |
|------|----------------|-----------------|
| A1 | — | — |
| A2 | — | — |
| A3 | — | — |
| A4 | — | — |
| A5 | ~~B2~~ (deferred, use query tool) | A1-A3 (quality of memory files to backfill into) |
| B1 | — | — |
| B2 | — | — |
| B3 | A4 | A1-A3 (quality), B1 (not blocking) |
| C1 | — | A4 (conventions) |
| C2 | A1 | ~~B2~~ (deferred, use `data/*.json` directly) |
| C3 | B1 | C1 (coverage) |
| D1 | B3 | — |
| D2 | B3, D1 | — |
| D3 | C2 | — |
| D4 | B3 | D1 |

## Spec Risk Watch List

Technologies requiring ongoing monitoring for spec changes:

| Technology | Risk | What to Watch |
|---|---|---|
| UCAN | Medium | Pre-1.0 RC, JWT→IPLD migration, ucan-wg repos |
| IPNI | Medium | Reader privacy (IPIP-0421) may change query patterns |
| PDP | Medium-High | New (2025), smart contract interfaces may evolve |
| DASL | Watch | Potential IETF standards track for CID/CAR |

## Success Criteria

**Knowledge system (Phase A + C; B2 deferred):**
- Freshness score: 4/10 → 7+/10 (staleness headers + validation script)
- All memory/tech/ files have authoritative spec links
- `.claude/rules/` directory with path-scoped JS/Go activation working
- Skills replace commands (same git-based team sharing)
- Multi-repo coverage: 21/82 → 82/82 repos with CLAUDE.md
- Validation script catches known stale claims on first run
- Stateless MCP server answers structured queries in <1s with <500 tokens per response
- All 10 MCP tools return accurate, formatted results
- Scanner data coverage in memory: service graph 9%→60%+, Go infra 0%→80%+, SQL schemas 0%→70%+
- "What infra does Piri use?" answerable via MCP tool call (vs. impossible today)

**Development workflow (Phase B):**
- Developer can say "I want to build X" and the AI guides them through value-first planning
- Feature brief produced in 5-10 min for typical features, feels helpful not bureaucratic
- Task decomposition produces concrete, completable tasks (1-2 files, <4 hours each)
- "Stop and re-decompose" rule is documented and followed
- End-to-end: Specify → Design → Decompose → Implement works smoothly
- Team members can use the same workflow via git (skills + templates + hooks committed)

**Enforcement (Phase B — B3-E):**
- Phase-gate hook blocks a write violation during testing (proves the gate works)
- TDD-guard hook prevents implementation before tests in a controlled test
- Test-modification-detector catches a simulated test weakening
- Developers can complete Tier 0 tasks without friction from hooks
- Hook escape procedures documented and work as described
- No false-positive blocks in normal development after 1 week of use

**Process (Phase D):**
- Reviewer subagent catches at least 1 issue per feature that self-audit missed
- Subagent delegation guidance is in CLAUDE.md and used by team
- CI freshness pipeline runs weekly and creates accurate drift reports
- Feedback loop captures pain points and drives at least 1 rule/hook improvement per month

**The acid test:** A developer new to the Storacha codebase can:
1. Run `/plan` and be guided through planning a feature
2. Get a feature brief that the AI then executes against
3. Have hooks prevent common mistakes without feeling blocked
4. See the reviewer catch something they would have missed
5. Feel like the 10 minutes of planning made the next 4 hours of coding faster and better

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-02-19 | alex + claude | Initial draft from 4-stream research synthesis |
| 2026-02-19 | alex + claude | Major expansion of B3: integrated lean PRD + SDD into unified 4-phase workflow. Added 5th research stream (lean PRD, 40+ sources). Updated execution order, success criteria, acid test. |
| 2026-02-19 | alex + claude | Integrated TDD (7th research stream) + workflow benchmarking into B3. Added Tier 0 escape hatch, parallel markers [P], self-audit instruction, TDD guards, anti-pattern table, research data table. Updated feature brief template with acceptance criteria + test references. Research report: `research/tdd-ai-agents.md`. |
| 2026-02-19 | alex + claude | Added B3-E enforcement architecture (8th research stream). 31 procedural gaps audited. Added 3-layer defense-in-depth: rules (2 files), hooks (5 hooks: phase-gate, tdd-guard, test-modification-detector, workflow-nudge, red-test-verification), CI (2 pre-commit hooks). Added subagent isolation for context pollution prevention, self-audit hardening, enforcement summary matrix. Research report: `research/enforcement-mechanisms.md`. |
| 2026-02-19 | alex + claude | Plan review and structural fixes: (1) Added `Status: pending` to all 17 items. (2) Expanded Phase C (C1-C3) with full approach, validation, deliverables. (3) Expanded Phase D (D1-D4) with full approach — D1 reviewer subagent now has review-point specs and output format, D3 has full CI workflow YAML, added D4 feedback loop. (4) Added meta-plan dependency graph with critical path and parallelizable groups. (5) Consolidated B3 deliverables into 14-item master list. (6) Fixed B3 dependency: A4 not B1. (7) Added hook escape procedures. (8) Added enforcement success criteria. (9) Fixed phase-gate hook for single-spec enforcement. (10) Replaced agent-based test-mod-detector with bash pre-filter. |
| 2026-02-19 | alex + claude | Scanner data analysis (9th research stream). Found memory files cover only 9% of service graph, 0% of SQL schemas, 0% of Go service infra. Promoted B2 from deferred to active with full MCP server spec (10 tools, stateless in-memory architecture). Added A5 (backfill scanner data into memory files). Updated C2 to use MCP/JSON as data source. Updated CLAUDE.md (JSON output files removed, MCP planned). Updated dependency graph with two critical paths. Added MCP success criteria. Research report: `research/scanner-data-coverage.md`. |
| 2026-02-19 | alex + claude | B2 updated: removed SQLite, switched to fully stateless architecture. JSON files committed to git (diffable), loaded into memory at startup. No database, no generated artifacts, no state. |
| 2026-02-20 | alex + claude | B2 deferred: scanners require local repo clones (579MB), not practical for new team members. GitHub API rewrite is the right fix but not priority now. Workaround: scanner JSON committed to `data/`, query tool works without repos. Updated A5 and C2 dependencies to use query tool/JSON fallback. Unblocked A5 and C2 from B2 dependency. Updated critical paths, parallelizable groups, success criteria. |
| 2026-02-20 | alex + claude | **Full execution complete.** All 14 active items (B2 deferred) implemented in 3 waves. Wave 1: A1-A4, B1, C1 (memory headers, spec refs, TL;DRs, rules dir, skills migration, CLAUDE.md generator). Wave 2: A5, B3, C2, C3 (scanner backfill, unified dev workflow with 14 deliverables, freshness validator, discover skill). Wave 3: D1-D4 (reviewer subagent, subagent docs, CI pipeline, feedback loop). Plan status → `done`. |
