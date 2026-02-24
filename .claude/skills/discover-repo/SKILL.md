---
name: discover-repo
description: "Systematically explore a repo to understand its structure, patterns, and conventions"
user_invocable: true
---

# Discover a repo's structure, patterns, and conventions

Perform a structured exploration of a Storacha repository to understand what it does, how it works, and how it fits into the broader system.

## Usage

The user will specify a repo name. For example:
- `/discover go-ucanto`
- `/discover freeway`
- `/discover piri`

## Instructions

Read the argument provided by the user (`$ARGUMENTS`). This is the repo name to explore.

### Step 0: Locate the Repo

1. Look for the repo at `{repo-name}/` (sibling of `aidev/` at the project root).
2. If not found, check for close name matches (e.g., "upload-service" vs "upload_service", "w3up" vs "w3-up").
3. If still not found, tell the user the repo is not cloned and suggest:
   ```
   gh repo clone storacha/{repo-name}
   ```
4. Stop and wait for the user before continuing.

### Step 1: Product Context (cross-cutting data)

Before diving into files, gather context from the pre-computed data:

1. Run `python aidev/tools/query.py repo {repo-name}` to get the comprehensive repo overview (product membership, role, tech stack, capabilities, infrastructure).
2. Run `python aidev/tools/query.py graph {repo-name}` to see service graph edges (what this repo calls and what calls it).
3. Note the product group, role description, and any capabilities already known.

### Step 2: Manifest Scan

Read the project manifest to identify language, dependencies, and available scripts:

- **JavaScript/TypeScript repos:** Read `{repo-name}/package.json`. If it has a `workspaces` field, this is a monorepo — also read `packages/*/package.json` for each workspace.
- **Go repos:** Read `{repo-name}/go.mod`. Check for `cmd/` directory for CLI entry points.
- **Hybrid repos:** Some repos have both. Check for both `package.json` and `go.mod`.

Extract and note:
- Language(s) and runtime (Node.js, Cloudflare Worker, Go binary, etc.)
- Key dependencies (especially `@ucanto/*`, `@storacha/*`, `@web3-storage/*`, `go-ucanto`, `go-libstoracha`)
- Available scripts (`npm run`, `make`, `go build`)
- Monorepo structure if applicable (list workspace packages)

### Step 3: Entry Point Mapping

Find the main entry points based on what Step 2 revealed:

**For JS repos:**
- Read `src/index.js` or `src/index.ts` (or the `main`/`module` field from package.json)
- Check for `wrangler.toml` or `wrangler.jsonc` (Cloudflare Worker)
- Check for `sst.config.*` or `stacks/` directory (SST infrastructure)
- Check for `bin/` directory or `"bin"` field in package.json (CLI tool)

**For Go repos:**
- Read `cmd/main.go` or `cmd/*/main.go` (CLI entry points)
- Check for `internal/` vs `pkg/` directory layout
- Look for HTTP handler setup (mux/chi/gin/net-http)

**For monorepos:**
- Identify the "main" package (usually the one with the service entry point)
- Map which packages are libraries vs services vs CLIs

### Step 4: Pattern Recognition

Classify the repo by matching against known Storacha patterns. Read the relevant files to confirm each pattern:

| Pattern | Indicators | Classification |
|---------|-----------|----------------|
| **ucanto service** | Imports `@ucanto/server` or `go-ucanto/server`, has `Server.create()` or `server.NewServer()` | UCAN RPC service handler |
| **ucanto client** | Imports `@ucanto/client` or `go-ucanto/client`, invokes capabilities | Client library |
| **Cloudflare Worker** | Has `wrangler.toml`, exports `fetch` handler, uses `env` bindings | Edge service |
| **SST infra** | Has `sst.config.ts`, `stacks/` directory, `@serverless-stack/*` deps | Infrastructure-as-code |
| **CLI tool** | Has `bin/` or commander/yargs/urfave-cli deps, `"bin"` in package.json | Developer tool |
| **Library** | No entry point, only exports, consumed by other packages | Shared library |
| **Gateway middleware** | Uses `composeMiddleware`, `withX` naming pattern | Gateway extension |
| **Go service (uber/fx)** | Uses `fx.New()`, `fx.Module()`, `fx.Provide()` | Go dependency-injected service |
| **Content claims** | Works with `assert/*` capabilities, location/partition/relation claims | Claims subsystem |
| **Filecoin pipeline** | Works with `piece/*`, `aggregate/*`, `deal/*`, CommP | Filecoin subsystem |

Note which patterns match. A repo may match multiple patterns (e.g., Cloudflare Worker + ucanto service).

### Step 5: Capability & Handler Discovery

If the repo is a UCAN service or client:

**JS repos:** Search for:
- `Server.provide(` or `Server.provideAdvanced(` — these are capability handlers
- `.invoke(` — these are capability invocations (client-side)
- Capability imports from `@storacha/capabilities` or `@web3-storage/capabilities`

**Go repos:** Search for:
- `server.Provide(` or `server.WithServiceMethod(` — capability handlers
- Capability imports from `go-libstoracha/capabilities`

List each capability handled or invoked, with the file path.

### Step 6: Test Infrastructure

Identify the testing setup:

**JS repos:**
- Look for `test/` or `__tests__/` directory
- Read `package.json` for test scripts and test framework deps (mocha, vitest, jest, miniflare)
- Check for `test/helpers/` (shared test fixtures, ed25519 signers)
- Check for `.env.test` or test-specific configuration

**Go repos:**
- Look for `*_test.go` files
- Check for `testdata/` directories
- Check for mockery configuration (`mockery.yaml` or `.mockery.yaml`)
- Check for `internal/testutil/` or similar test helper packages

Note the test command(s), framework, and any special test infrastructure (e.g., miniflare for CF Workers, Docker for integration tests).

### Step 7: Infrastructure Dependencies

If the repo is a deployed service:

1. Run `python aidev/tools/query.py infra {repo-name}` to see infrastructure resources.
2. Look for:
   - DynamoDB table definitions (`Table` in SST or `dynamodb` in config)
   - R2/S3 bucket references
   - SQS/queue configuration
   - KV namespace bindings (Cloudflare)
   - D1 database bindings
   - Environment variables that reference other services

### Step 8: Dependency Blast Radius

Cross-reference the repo's key exports against `aidev/memory/architecture/shared-packages.md`:

1. Read `aidev/memory/architecture/shared-packages.md`.
2. Determine which blast radius tier the repo's packages fall into.
3. Identify which other repos depend on this repo's packages.
4. Run `python aidev/tools/query.py impact {repo-name}` for the full dependency analysis.

### Step 9: Check for Existing CLAUDE.md

Check if `aidev/repo-guides/{repo-name}.md` already exists:

- **If it exists:** Read it and compare against your findings. Note any gaps or outdated information. Prepare enhancement suggestions.
- **If it does not exist:** Draft a new CLAUDE.md following the established template (see Output Format below).

## Output Format

Present the exploration results in this structured format:

```
## Repo Discovery: {repo-name}

### Identity
- **Product group:** (from product-map.json)
- **Role:** (1-line description)
- **Language:** JS/Go/Hybrid
- **Runtime:** Node.js / Cloudflare Worker / Go binary / etc.
- **Pattern(s):** (from Step 4 classification)

### Structure
(Directory tree of key paths, like existing CLAUDE.md files)

### Entry Points
- **Main:** (file path and what it does)
- **CLI:** (if applicable)
- **HTTP:** (handler setup location)

### Capabilities
| Capability | Role | File |
|-----------|------|------|
| `domain/verb` | handler/client | `path/to/file` |

### Dependencies
- **Key imports:** (high-blast-radius packages this repo uses)
- **Blast radius tier:** (if this repo exports packages others consume)
- **Service graph:** (what this repo calls, what calls it)

### Test Infrastructure
- **Framework:** (mocha/vitest/testify/etc.)
- **Command:** (how to run tests)
- **Fixtures:** (shared test helpers, ed25519 signers, etc.)

### Infrastructure
(DynamoDB tables, R2 buckets, queues, KV namespaces — if applicable)

### CLAUDE.md Status
- **Exists:** yes/no
- **Action:** (draft new / suggest enhancements / up-to-date)
```

If a new repo guide is needed, draft it following the format of existing ones (see `aidev/repo-guides/freeway.md` and `aidev/repo-guides/piri.md` as templates). The guide should include:
1. One-line repo description
2. Quick Reference (build/test commands)
3. Structure (key directory tree)
4. Capabilities handled/invoked (if UCAN service/client)
5. Key patterns (repo-specific conventions)
6. What breaks if you change things here

Present the draft to the user for review before writing it. Ask if there are any undocumented conventions or tribal knowledge to include.

## Tips

- For monorepos, focus the exploration on the most important 3-5 packages, not every single one.
- If `aidev/tools/query.py` returns no data for a repo, it may be too new or not yet scanned. Fall back to direct file exploration.
- Some repos have a `README.md` that provides useful context — skim it but don't rely on it as the source of truth (code over specs).
- For Go repos, the `go.sum` file reveals the full transitive dependency tree but is usually too large to read. Focus on `go.mod` direct dependencies.
- When classifying patterns, check both `src/` and `lib/` directories — some repos use one convention, some the other.
