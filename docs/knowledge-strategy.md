# Storacha Knowledge Strategy

> Goal: Make Claude Code an expert-level collaborator — better than any senior dev or architect — on the Storacha codebase and its niche technology stack.

## Current State

### What We Have

**Scanner data (raw):**

| Artifact | Content | Location |
|----------|---------|----------|
| Product map | 82 repos, roles, deps, tech | `aidev/data/product-map.json` |
| Infrastructure map | DBs, buckets, queues, schemas | `aidev/data/infrastructure-map.json` |
| API surface map | 175 UCAN capabilities, 231 service graph edges | `aidev/data/api-surface-map.json` |
| Concept inventory | 150+ niche deps, ~100 concepts, P0-P3 | `aidev/data/concept-inventory.md` |

**Source material:**

| Artifact | Content | Location |
|----------|---------|----------|
| Specs | 24 w3 protocol specs | `specs/` (working repo) |
| RFCs | 13 design RFCs | `RFC/rfc/` (working repo) |
| Ucanto docs | 8 package READMEs | `ucanto/packages/*/README.md` (working repo) |
| Website docs | 22+ pages (concepts, how-to, API) | `docs/` (working repo) |

**Knowledge system (5 layers):**

| Layer | Artifact | Location |
|-------|----------|----------|
| 1 | Root CLAUDE.md — routing table, architecture, conventions | `CLAUDE.md` |
| 2 | 27 memory files — tech patterns, flows, architecture | `aidev/memory/` |
| 3 | 21 per-repo guides — repo-specific context | `aidev/repo-guides/<repo>.md` |
| 4 | 4 slash commands — /trace, /impact, /spec, /new-capability | `.claude/skills/` |
| 5 | Query tool — cross-cutting queries over scanner JSONs | `aidev/tools/query.py` |

### Technology Landscape (from concept scan)

The codebase uses **~150 niche dependencies** across JS and Go, spanning 10 domain areas:

| Domain | JS Pkgs | Go Mods | Repos Affected | Claude's Starting Knowledge |
|--------|---------|---------|----------------|-----------------------------|
| UCAN/ucanto | 9 | 2 | 30+ | Low — custom framework |
| IPLD/DAG formats | 7 | 8 | 25+ | Partial — know concept, not wire format |
| Multiformats (CID, multihash) | 8 | 10 | 40+ | Partial — know concept, not construction details |
| Filecoin pipeline | 6 | 25+ | 15+ | Low — CommP/FR32/aggregation is highly niche |
| IPFS core | 8 | 20+ | 20+ | Medium — know IPFS, not internal APIs |
| libp2p networking | 13 | 15+ | 12+ | Low-Medium — know concept, not Go usage |
| IPNI (content indexing) | 2 | 4 | 8+ | Very Low — specialized protocol |
| Crypto (ed25519, P-256, AES) | 7 | 5 | 15+ | Medium — standard crypto, specific usage |
| Pail/CRDT structures | 2 | 1 | 4+ | Very Low — custom data structure |
| Content Claims | 3 | 2 | 8+ | Very Low — custom protocol |

**Priority breakdown: ~35 P0-Critical concepts, ~30 P1-High, ~20 P2-Medium, ~15 P3-Low**

Full inventory: `aidev/data/concept-inventory.md`

### Gaps (All Addressed)

| Gap | Resolution |
|-----|------------|
| Distilled technology patterns | 12 `aidev/memory/tech/` files covering P0-P1 concepts with code examples and gotchas |
| End-to-end flow traces | 5 `aidev/memory/flows/` files tracing upload, retrieval, auth, filecoin, egress |
| Spec-to-implementation mapping | `aidev/memory/architecture/spec-implementation-map.md` — 24 specs, 47 capabilities, 9 divergences |
| Cross-repo impact / contract boundaries | `aidev/memory/architecture/shared-packages.md` + blast-radius tiers in root CLAUDE.md |
| Infrastructure decision rationale | `aidev/memory/architecture/infrastructure-decisions.md` |
| Knowledge delivery layer | 5-layer system: root CLAUDE.md, memory files, per-repo CLAUDE.md, slash commands, query tool |

---

## Analysis Pipeline

### Phase 1: Technology Pattern Extraction

Now that we have the concept inventory (P0-P3 prioritized), Phase 1 focuses on the **~35 P0-Critical** and **~30 P1-High** concepts.

**Study areas (ordered by priority):**

1. **ucanto RPC framework** (P0) — capability definition, Server.provide/provideAdvanced, service factories, effect system, connection model, CAR-encoded transport
   - Key files: `ucanto/`, `upload-service/packages/capabilities/src/`, `upload-service/packages/upload-api/src/`
2. **Content Claims + Indexing** (P0) — claim types (location, inclusion, index, relation, equals, partition), IPNI bridge, Sharded DAG Index
   - Key files: `content-claims/`, `indexing-service/`, `upload-service/packages/blob-index/`
3. **Filecoin pipeline** (P0) — CommP/FR32/aggregation, storefront→aggregator→dealer→deal-tracker, PDP, inclusion proofs
   - Key files: `upload-service/packages/filecoin-api/`, `data-segment/`, `fr32-sha2-256-...`, `piri/`
4. **Content addressing internals** (P1) — CID construction, multihash binary format, multicodec codes used, DAG-CBOR encoding, block/blockstore patterns
   - Key files: throughout, focus on `multiformats` usage patterns
5. **Pail & distributed data structures** (P0) — prolly tree, shard model, CRDT merge, Merkle clock
   - Key files: `pail/`, `go-pail/`
6. **Encryption model** (P0) — KEK/DEK, ucan-kms, key wrapping
   - Key files: `upload-service/packages/encrypt-upload-client/`, `ucan-kms/`
7. **Gateway/retrieval stack** (P0) — Freeway middleware, content serve auth, blob-fetcher batching
   - Key files: `freeway/src/`, `blob-fetcher/`, `gateway-lib/`

For each area, extract from actual code (not specs):
- **Our abstractions** — wrappers, helpers, patterns built on top of raw primitives
- **Canonical code examples** — from OUR codebase. "This is how WE create a capability. This is how WE build a CAR."
- **Gotchas** — where implementation diverges from what you'd expect reading the spec
- **Key types/interfaces** — TypeScript types and Go structs that define the contracts

**Approach:** Build targeted scanners + manual deep-reads of key files, then distill into concise pattern guides.

**Output:** `aidev/memory/tech/` files (one per technology area)

**Status:** COMPLETE — 12 memory/tech/ files written, validated (23/24 PASS)

### Phase 2: End-to-End Flow Tracing

Trace the critical paths through the entire system:

1. **Upload flow**: client SDK -> upload-api -> blob allocation -> R2 storage -> indexing -> filecoin pipeline
2. **Retrieval flow**: HTTP request -> freeway/gateway -> content-claims -> indexing-service -> blob-fetcher -> R2
3. **Auth flow**: email -> access/authorize -> session -> delegation chain -> capability invocation
4. **Filecoin deal flow**: storefront -> aggregator -> dealer -> deal-tracker -> on-chain
5. **Egress tracking**: freeway -> queue -> egress-consumer -> upload-api -> usage/billing

For each trace: which repos, which functions, which UCAN capabilities, which infra, step by step.

**Approach:** Code-level tracing using scanner outputs as the map, then walking the actual code to confirm.

**Output:** `aidev/memory/flows/` files (one per flow)

**Status:** COMPLETE — 5 flow files written (upload, retrieval, auth, filecoin-deal, egress-tracking)

### Phase 3: Spec-to-Implementation Mapping

For each of the 24 specs:
- Which repo(s) implement it
- Which capabilities from the spec are wired up in service handlers
- Extensions beyond the spec
- Unimplemented sections
- Status reality check ("RELIABLE" — does it match reality?)

**Approach:** Cross-reference `api-surface-map.json` capability catalog against spec content.

**Output:** `aidev/memory/architecture/spec-implementation-map.md`

**Status:** COMPLETE — 24 specs mapped, 47 capabilities tracked (41 implemented, 6 missing/partial), 9 key divergences documented

### Phase 4: Contract Boundary & Impact Analysis

Map the typed interfaces between services:
- Types/schemas that cross service boundaries
- Where a change in service A's types forces changes in B, C, D
- Shared packages that multiple services depend on (blast-radius packages)
- Version coupling between packages in the monorepo

**Approach:** Analyze package.json dependency chains, shared type imports, capability definitions consumed across repos.

**Output:** `aidev/memory/architecture/shared-packages.md`, impact rules in root CLAUDE.md

**Status:** COMPLETE — JS blast-radius (40+ shared packages), Go blast-radius (14 shared modules), w3up/upload-service migration mapped

---

## Knowledge Delivery Architecture

### Design Principle

A senior dev doesn't hold every line of code in their head. They have:
- A **mental model** of how things fit together
- **Pattern recognition** for the technologies
- Knowledge of **where to look**
- Awareness of **blast radius**
- Ability to **trace through** a system

The delivery layer replicates this, optimized for context window efficiency.

### Why a CLI Tool Instead of a Graph DB

Original decision to skip a graph DB was correct. The Layer 5 query tool (`aidev/tools/query.py`) fills the cross-cutting query gap with zero dependencies — just Python stdlib + the 3 scanner JSONs.

- **No infra needed**: no MCP server, no database process, no schema maintenance
- **Fast enough**: loads 3 JSONs, builds indexes in memory, answers in <1 second
- **Claude-native output**: markdown tables that Claude Code reads directly
- **Covers the gap**: the only queries Layers 1-4 couldn't handle were cross-file joins (capability→repo→infra→deps). The CLI tool handles exactly these.
- **If we outgrow it**: the index-building logic could be lifted into an MCP server, but there's no evidence we need that yet

### Layer 1: Root `CLAUDE.md` (~150 lines) — "The Router"

Always loaded into context. Contains:
- **Meta-instruction:** "Follow implementation patterns, not specs. When specs and code disagree, code is truth."
- **Architecture overview** in ~30 lines (the mental model)
- **Key conventions** (naming, error handling, testing patterns)
- **Routing table:** "For UCAN questions, read `aidev/memory/tech/ucan-patterns.md`; for upload flow, read `aidev/memory/flows/upload.md`"
- **Cross-repo impact rules:** "If you touch capabilities/ package, these 12 repos are affected"

**Status:** COMPLETE — root CLAUDE.md written (~100 lines with routing table, blast radius, conventions)

### Layer 2: Memory Files (~15-20 topic files) — "Deep Knowledge"

Located in `~/.claude/projects/.../memory/`. MEMORY.md always loaded; topic files searched on demand.

```
memory/
  MEMORY.md                              <- always loaded, index + top-level facts
  tech/
    ucanto-framework.md                  <- capability(), Server.provide(), service factories,
                                            connection model, CAR transport, effect system (P0)
    content-addressing.md                <- CID construction, multihash binary format, multicodec
                                            codes, DAG-CBOR encoding, blocks, blockstores (P1)
    car-unixfs.md                        <- CAR packing/unpacking, UnixFS chunking, DAG-PB,
                                            sharding strategies (P1-P2)
    filecoin-pipeline.md                 <- CommP, FR32, data aggregation, inclusion proofs,
                                            storefront/aggregator/dealer/deal-tracker, PDP (P0)
    content-claims-indexing.md           <- claim types (location/inclusion/index/relation/equals),
                                            Sharded DAG Index, IPNI advertisements, content
                                            routing bridge (P0)
    pail-data-structures.md              <- prolly trees, shard model, CRDT merge semantics,
                                            Merkle clock, ShardBlock/ShardEntry (P0)
    encryption-kms.md                    <- KEK/DEK model, ucan-kms, key wrapping, P-256/ECDH,
                                            AES-GCM content encryption (P0)
    gateway-retrieval.md                 <- Freeway middleware stack, content serve auth,
                                            blob-fetcher batching, multipart byte-range (P0)
    ucan-auth-model.md                   <- delegation chains, proof resolution, attestation
                                            signatures, did:mailto, revocation protocol (P0)
    libp2p-networking.md                 <- connection model, multiaddr, bitswap, pubsub,
                                            Go-specific patterns (P1)
    go-ecosystem.md                      <- go-ucanto vs JS ucanto differences, go-libstoracha,
                                            go-cid/go-ipld-prime patterns (P0-P1)
  flows/
    upload-flow.md                       <- end-to-end upload trace
    retrieval-flow.md                    <- end-to-end retrieval trace
    auth-flow.md                         <- authorization chain
    filecoin-deal-flow.md                <- storage deal lifecycle
    egress-tracking-flow.md              <- egress -> billing
  architecture/
    service-profiles.md                  <- each service: owns, exposes, depends on
    infrastructure-decisions.md          <- why these infra choices
    shared-packages.md                   <- blast-radius packages, version coupling
    spec-implementation-map.md           <- spec -> code, divergences
```

**Status:** COMPLETE — 27 files: 12 tech/, 5 flows/, 3 architecture/, MEMORY.md + 6 research files
- P0-Critical: fully covered (35/35 concepts)
- P1-High: fully covered (30/30) — filecoin, IPNI, networking deepened
- P2-Medium: mostly covered (~18/20) — GraphSync, WebRTC, QUIC confirmed NOT USED
- P3-Low: partially covered — Filecoin actors documented via forgectl/piri-signing-service

### Layer 3: Per-Repo `CLAUDE.md` — "Working Context"

Only loaded when working in a specific repo. Generate for the ~15 most critical repos:
- upload-service, freeway, content-claims, indexing-service, ucanto
- w3infra, w3up, blob-fetcher, egress-consumer, gateway-lib
- reads, w3clock, ucan-kms, w3filecoin-infra, piri

Each contains:
- What this service does (3 lines)
- Key files to know about
- Local patterns and conventions
- What breaks if you change things here
- How to test

**Status:** COMPLETE — 21 CLAUDE.md files (19 new + 2 existing). Covers: upload-service, freeway, content-claims, indexing-service, ucanto, w3infra, w3up, blob-fetcher, w3clock, ucan-kms, w3filecoin-infra, piri, etracker, gateway-lib, guppy, tg-miniapp, delegator, piri-signing-service, storoku, forgectl, filecoin-services.

### Layer 4: Slash Commands / Skills — "Workflows"

Custom commands for repeated development tasks:
- `/trace <flow-name>` — load the relevant flow trace into context
- `/impact <package-or-capability>` — show what's affected by a change
- `/spec <spec-name>` — load the spec + our implementation mapping
- `/new-capability` — step-by-step guide for adding a UCAN capability
- `/review-compliance <spec>` — check implementation against spec (future)

**Status:** COMPLETE — 4 commands in `.claude/skills/`: trace, impact, spec, new-capability. `/review-compliance` deferred (can be built on top of /spec when needed).

### Layer 5: Structured Query Tool

CLI tool wrapping all 3 scanner JSONs for cross-cutting queries that require joining data across repos, capabilities, infrastructure, and service graphs.

- `aidev/tools/query.py` — single-file Python CLI (~350 lines)
- Loads `api-surface-map.json`, `infrastructure-map.json`, `product-map.json`
- Builds in-memory indexes: capability→repos, repo→capabilities, repo→infra, service graph adjacency
- 6 query modes: `capability`, `impact`, `infra`, `graph`, `product`, `repo`
- Output: concise markdown tables readable by Claude Code

**Status:** COMPLETE — `aidev/tools/query.py` implemented, `/impact` command updated with query tool fallback reference

---

## Build Order

All phases complete:

```
Phase 1: Technology pattern extraction        COMPLETE — 12 tech/ memory files
Phase 2: End-to-end flow tracing              COMPLETE — 5 flows/ memory files
Phase 3: Spec mapping + contract analysis     COMPLETE — architecture/ memory files
Phase 4: Delivery assembly                    COMPLETE — CLAUDE.md, MEMORY.md, 21 per-repo files, 4 slash commands
Phase 5: Query tool + evaluation              COMPLETE — tools/query.py, stale sections cleaned up
```

Meta-instructions finalized in root CLAUDE.md (5 rules: code over specs, pattern over principle, check blast radius, trace before coding, test like we test).

---

## Completed Analysis Steps

- [x] Product/repo mapping (82 repos cataloged with roles, deps, tech)
- [x] Infrastructure scanning (DBs, buckets, queues, schemas across all repos)
- [x] API surface scanning (91 HTTP routes, 175 UCAN capabilities, 149 handlers, 231 service graph edges)
- [x] Concept inventory (150+ niche dependencies, ~100 domain concepts, P0-P3 prioritized)
- [x] Spec catalog (24 specs, 13 RFCs, ucanto docs, website docs inventoried)

## Scanner Artifacts

| Scanner | Script | Output |
|---------|--------|--------|
| API surface | `aidev/scripts/scan_api_surface.py` | `aidev/data/api-surface-map.{txt,json}` |
| Infrastructure | `aidev/scripts/scan_infra.py` | `aidev/data/infrastructure-map.{txt,json}` |
| Product map | `aidev/scripts/scan_products.py` | `aidev/data/product-map.json` |
| Concept inventory | (manual synthesis) | `aidev/data/concept-inventory.md` |

Note: `aidev/scripts/scan_infra.py` requires `aidev/data/repos-config.yaml` (auto-generated from cloned repos).

## Improvement Plans

Process improvement proposals are tracked in `AIPIP/`:

| AIPIP | Title | Status |
|-------|-------|--------|
| [AIPIP-0001](AIPIP/AIPIP-0001-knowledge-system-v2.md) | Knowledge System v2 — Research-Backed Improvements | done |

See `AIPIP/README.md` for the AIPIP format and conventions.

---

## Open Questions (Resolved)

- [x] **Per-repo CLAUDE.md location?** → `aidev/repo-guides/<repo>.md`. These are tailored for Claude Code, not human contributors. If we want to upstream them, they'd need editing for a human audience. Keep here for now.
- [x] **Scanner regeneration cadence?** → On-demand. Scanners are cheap to re-run (`scan_api_surface.py`, `scan_infra.py`, `final_analysis.py`). Re-run when repos have significant structural changes (new services, capability changes, infra migrations). No need for automated cadence — the data changes slowly.
- [x] **Separate onboarding doc for humans?** → Not needed yet. The CLAUDE.md files are machine-oriented but readable by humans. If a human onboarding need arises, distill from `KNOWLEDGE_STRATEGY.md` + root `CLAUDE.md` into a prose document. The knowledge is all here; only the format would change.
- [x] **Slash commands: scanner JSON or memory files?** → Memory files for the primary path (distilled, token-efficient). Layer 5 query tool (`aidev/tools/query.py`) as fallback for cross-cutting queries that need raw data joins. `/impact` command references both.
- [x] **Service profiles granularity?** → One file (`aidev/memory/architecture/infrastructure-decisions.md`) for infra decisions, plus 21 per-repo CLAUDE.md files for service-specific context. This hybrid works well — the per-repo files cover "what this service does" while the architecture file covers cross-cutting infra patterns.
- [x] **Scanners vs manual code reading?** → Hybrid, as predicted. Scanners for structural extraction (capabilities, deps, infra). Manual deep-reads for pattern understanding (how ucanto works, auth model, etc.). The 12 tech files were all manual synthesis informed by scanner data.
- [x] **JS/Go duality?** → Handled via `aidev/memory/tech/go-ecosystem.md` (Go-specific patterns, differences from JS ucanto) plus per-repo CLAUDE.md files for Go repos (piri, indexing-service, etracker). Cross-cutting tech files (content-claims-indexing, filecoin-pipeline) cover both JS and Go where applicable.
