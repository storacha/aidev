# Storacha Codebase — Claude Code Instructions

## Meta-Rules

1. **Code over specs.** When implementation and spec disagree, follow the implementation. Flag the divergence but don't "fix" toward the spec without explicit instruction.
2. **Pattern over principle.** Don't invent new patterns. Find how the codebase already does it and follow that.
3. **Check blast radius.** Before changing a shared package or capability, consult `aidev/memory/architecture/shared-packages.md`.
4. **Trace before coding.** For cross-service changes, load the relevant flow trace from `aidev/memory/flows/` first.
5. **Test like we test.** Follow existing test patterns per repo. JS: Mocha + shared test suites. Go: testify + mockery.

## Architecture Overview

Storacha is a decentralized storage network built on UCAN-based RPC (ucanto). 82 repos, JS + Go.

**Core data flow:** Client encodes file as UnixFS blocks, shards into ~127MB CARs, uploads each shard via `blob/add` to R2/S3, indexes via `index/add` (IPNI + content claims), registers via `upload/add`. Retrieval via Freeway gateway fetches blocks using byte-range requests from R2.

**Auth model:** Spaces (ed25519 keypairs) delegate to accounts (did:mailto) via recovery delegation. Accounts delegate to agents via session proofs (absent-signed delegation + service attestation). Every invocation carries a proof chain: space -> account -> agent -> service.

**Key services:**

| Service | Repo | Language | Role |
|---|---|---|---|
| Upload API | upload-service / w3up | JS | Blob/upload/index/filecoin handlers |
| Freeway | freeway | JS (CF Worker) | IPFS gateway with UCAN auth, 26 middlewares |
| Indexing Service | indexing-service | Go | Content routing (IPNI + claims) |
| Piri | piri | Go | Storage node (PDP proofs, retrieval) |
| UCAN KMS | ucan-kms | JS (CF Worker) | Encryption key management |
| Content Claims | content-claims | JS | Claim storage and serving |
| w3clock | w3clock | JS (CF Worker) | Merkle clock (Pail CRDT) |
| Etracker | etracker | Go | Egress tracking for storage nodes |

**Two monorepos with overlapping packages:**
- `upload-service` — newer, `@storacha/*` namespace (16 packages)
- `w3up` — older, `@web3-storage/*` namespace (10 packages)
- 8 packages exist in both; prefer `upload-service` for active development

## Conventions

- **Capabilities:** `domain/verb` naming (e.g., `blob/add`, `space/info`). Defined in `@storacha/capabilities`.
- **Error handling:** `Result<T,X>` discriminated union (`{ ok }` or `{ error }`). `Failure` base class with `.name` string matching. Go: `result.Result[O,X]`.
- **Effects:** `fork()`/`join()` on `OkBuilder` for async workflows. `ucan/await` references receipts.
- **JS files:** kebab-case. Go files: snake_case.
- **Imports:** `@storacha/*` (new), `@web3-storage/*` (legacy), `@ucanto/*` (stable). Go: `github.com/storacha/*`.
- **Testing:** JS: Mocha + object-map test suites passed to `testVariant`. Go: testify assertions + mockery mocks. Shared ed25519 fixtures for deterministic DIDs.

## Knowledge Routing Table

| Need to... | Read |
|---|---|
| Define/modify UCAN capabilities | `aidev/memory/tech/ucanto-framework.md` |
| Work with CIDs, multihash, codecs | `aidev/memory/tech/content-addressing.md` |
| Create/parse CAR files, shard uploads | `aidev/memory/tech/car-unixfs.md` |
| Understand auth, delegations, sessions | `aidev/memory/tech/ucan-auth-model.md` |
| Work with content claims, IPNI, indexing | `aidev/memory/tech/content-claims-indexing.md` |
| Understand Filecoin pipeline, CommP | `aidev/memory/tech/filecoin-pipeline.md` |
| Work with Pail KV, CRDT, Merkle clock | `aidev/memory/tech/pail-data-structures.md` |
| Understand gateway, middleware stack | `aidev/memory/tech/gateway-retrieval.md` |
| Work with encryption, KMS | `aidev/memory/tech/encryption-kms.md` |
| Build Go services, go-ucanto | `aidev/memory/tech/go-ecosystem.md` |
| Error handling, testing, naming patterns | `aidev/memory/tech/cross-cutting-patterns.md` |
| Trace: upload end-to-end | `aidev/memory/flows/upload-flow.md` |
| Trace: retrieval via gateway | `aidev/memory/flows/retrieval-flow.md` |
| Trace: auth/login/delegation chains | `aidev/memory/flows/auth-flow.md` |
| Trace: Filecoin deal lifecycle | `aidev/memory/flows/filecoin-deal-flow.md` |
| Trace: egress tracking -> billing | `aidev/memory/flows/egress-tracking-flow.md` |
| Check spec vs implementation | `aidev/memory/architecture/spec-implementation-map.md` |
| Assess blast radius of a change | `aidev/memory/architecture/shared-packages.md` |
| Understand infra: SST, DynamoDB, R2, queues | `aidev/memory/architecture/infrastructure-decisions.md` |
| Decide when to use subagents | `.claude/rules/subagent-patterns.md` |

## Blast Radius Quick Reference

**EXTREME caution (15+ repos affected):** `@ucanto/core`, `@ucanto/interface`, `@ucanto/principal`, `@ucanto/transport`, `@ipld/car`

**HIGH caution (10+ repos):** `@storacha/capabilities`, `@storacha/client`, `@ucanto/server`, `@ucanto/client`, `@ipld/dag-cbor`

**Go equivalents:** `go-ucanto` (12 repos), `go-libstoracha` (11 repos)

**Rule:** Adding new capabilities = safe. Changing existing capability schemas = dangerous (check all handler + client repos).

## Structural Codebase Data

Pre-computed structural data in `aidev/data/` from scanning all 82 repos.

**Data files:**
- `aidev/data/api-surface-map.json` — 175 UCAN capabilities, 231 service graph edges, handlers, routes
- `aidev/data/infrastructure-map.json` — DynamoDB tables, R2/S3 buckets, SQS queues, 57 SQL schemas across 32 repos
- `aidev/data/product-map.json` — 82 repos with roles, deps, tech stack, grouped into 15 products

**Scanners:** `aidev/scripts/scan_api_surface.py`, `aidev/scripts/scan_infra.py`, `aidev/scripts/scan_products.py`. Re-run when repos have significant structural changes.

**Query tool:** `python aidev/tools/query.py <command> [args]` — cross-cutting queries over all 3 data files.
Commands: `capability`, `impact`, `infra`, `graph`, `product`, `repo`.

## Working in Specific Repos

When working in a specific repo, read `aidev/repo-guides/<repo>.md` for repo-specific instructions. Available for: guppy, tg-miniapp, upload-service, freeway, content-claims, indexing-service, ucanto, w3infra, w3up, blob-fetcher, w3clock, ucan-kms, w3filecoin-infra, piri, etracker, gateway-lib, delegator, piri-signing-service, storoku, forgectl, filecoin-services.

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/trace <flow>` | Load an end-to-end flow trace (upload, retrieval, auth, filecoin, egress) |
| `/impact <package-or-capability>` | Assess blast radius of a change |
| `/spec <spec-name>` | Show spec-to-implementation mapping and divergences |
| `/new-capability` | Step-by-step guide for adding a UCAN capability |

## Enforcement Hooks

Process rules in `.claude/rules/` are enforced by hooks in `.claude/hooks/`, wired via `.claude/settings.json`. These provide Tier 2 enforcement (~90%+ compliance) on top of Tier 1 rules (~60-80%).

| Hook | Event | Blocks? | What it enforces |
|------|-------|---------|------------------|
| `session-resume.sh` | SessionStart | No | Re-injects active feature state (phase, tasks, git branch) on startup/resume/compact |
| `branch-protection.sh` | PreToolUse (Bash) | Yes | Blocks git commit/push on main when a feature is active |
| `pre-commit-checks.sh` | PreToolUse (Bash) | Yes | Verifies phase is implement/complete before commits |
| `phase-gate.sh` | PreToolUse (Edit/Write) | Yes | Blocks source files in specify/design, non-test files in decompose |
| `tdd-guard.sh` | PreToolUse (Edit/Write) | Yes | Blocks source files if no test snapshot exists |
| `test-mod-detector.sh` | PreToolUse (Edit/Write) | No (warns) | Flags acceptance test modifications during implement phase |
| `review-gate.sh` | PreToolUse (Edit/Write) | Yes | Blocks PHASE transitions without required review artifacts |
| `workflow-nudge.sh` | UserPromptSubmit | No | Injects phase context into every prompt |
| `stop-decompose-verify.sh` | Stop | Yes | Verifies all tests fail (RED) during decompose phase |

See `aidev/AIPIP/AIPIP-0005-session-continuity-enforcement.md` for the design rationale.

## Query Tool (Layer 5)

For cross-cutting queries that correlate data across repos, capabilities, infrastructure, and service graphs:

```bash
python aidev/tools/query.py capability blob/add          # Who defines/handles a capability
python aidev/tools/query.py capability --repo piri        # All capabilities for a repo
python aidev/tools/query.py impact indexing-service       # Full dependency + infra analysis
python aidev/tools/query.py impact @storacha/capabilities # Package reverse-dependency analysis
python aidev/tools/query.py infra freeway                 # Infrastructure resources for a repo
python aidev/tools/query.py infra --type dynamodb         # All repos using an infra type
python aidev/tools/query.py graph upload-service          # Service graph edges (in/out)
python aidev/tools/query.py repo piri                     # Comprehensive repo overview
python aidev/tools/query.py product "Upload Platform"     # Product details with all repos
```
