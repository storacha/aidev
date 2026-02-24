# Phase 1: Technology Deep Dive Procedure (v2)

> Revised after adversarial review against: Qodo Aware architecture, Code-Graph-RAG,
> Arbor (AST-based deterministic code intelligence), Anthropic 2026 Agentic Coding
> Trends Report, Martin Fowler's context engineering for coding agents, and the
> arxiv paper on AST-derived vs LLM-extracted knowledge graphs for code RAG.

## Adversarial Review: What Was Wrong With v1

| Problem | Why It's Bad | Fix |
|---------|-------------|-----|
| **Sequential topic-by-topic execution** | 11 topics × 6 steps = 66 serial steps. Extremely slow. | Batch all research in parallel (Phase 1A), then synthesize (1B). |
| **Spec-first ordering** | Violates our own "code is truth" principle. Starting with specs biases toward what SHOULD exist, not what DOES. | Code-first: discover patterns from code, THEN compare to spec. |
| **Ignores our own scanner data** | We already computed api-surface-map.json, infra-map.json, product-map.json — but the procedure starts fresh with grep/glob. Wasted work. | Use scanner outputs as the starting map for each topic. |
| **300-line file cap is arbitrary** | ucanto framework might need 500 lines. Forcing compression drops critical patterns. | Split large topics into focused sub-files. No hard cap — optimize for utility, not size. |
| **Spec diff is pointless for ~half the P0s** | Content Claims, Pail, ucanto, Freeway middleware — these are Storacha-original. There IS no external spec to diff against. | Only do spec diff where an external spec actually exists. For Storacha-original: document the design, not the "diff." |
| **No validation step** | How do we know a memory file is actually useful? "Tested against a question" is vague. | Define concrete test questions per topic. Try answering with ONLY the memory file. |
| **Missing cross-cutting patterns** | Error handling, testing, async patterns, import conventions cut across ALL topics. Procedure treats topics independently. | Add a cross-cutting patterns file assembled after all topics. |
| **No structural leverage** | Research shows AST-derived structural graphs get 15/15 accuracy vs 13/15 for text-based. We're entirely text-based. | Use our scanner data as a structural graph. It already has: capability → handler → service → route mappings. |
| **"One at a time" context strategy is too conservative** | Completing one topic before starting the next means N sessions. | Parallel subagents for research. Main context for synthesis. |

### Key Insight From Research

> "Comprehensive analysis upfront, leveraging pre-computed knowledge at runtime"
> — Qodo Aware architecture

> "Deterministic structure provides more reliable grounding than probabilistic extraction"
> — arxiv 2601.08773 (AST vs LLM graph comparison)

> "Claude Code employs a hybrid model: CLAUDE.md files are placed into context upfront,
> while glob and grep allow just-in-time retrieval. This avoids stale indexing."
> — Martin Fowler, Context Engineering for Coding Agents

Translation: Don't build a complex indexing system. DO pre-compute structural data (we already have this via scanners). DO write focused knowledge files. DO keep them searchable via simple tools.

---

## Design Principles (Revised)

1. **Code first, spec second.** Discover patterns from code. Use specs only as reference to understand divergences.
2. **Leverage what we've already built.** Scanner outputs are the structural map. Start there, not from scratch.
3. **Parallelize research, serialize synthesis.** Research (web search + code discovery) parallelizes perfectly. Synthesis (pattern extraction + writing) requires holding things together — do it sequentially but fast.
4. **Split, don't compress.** If a topic needs 500 lines, split into 2-3 focused files. Utility > arbitrary limits.
5. **Validate with real questions.** Every memory file must pass a test: can it answer "how do I do X?" without reading more code?
6. **Cross-cut last.** After all topics, extract patterns that span multiple topics (error handling, testing, conventions).

---

## Execution Architecture

### Phase 1A: Parallel Research Batch

**Run ALL of these simultaneously.** This is one session with many parallel agents.

```
┌──────────────────────────────────────────────────────────────┐
│  PARALLEL BATCH: Spec Acquisition (all 11 topics)            │
│                                                              │
│  Agent 1: Web search + fetch specs for topics 1-3            │
│    - CID/multihash/IPLD specs                                │
│    - CAR format spec, UnixFS spec                            │
│    - UCAN spec, ucanto README                                │
│                                                              │
│  Agent 2: Web search + fetch specs for topics 4-6            │
│    - DID methods specs                                       │
│    - Content Claims (our spec in /specs/)                    │
│    - Filecoin FRC-0058, CommP computation                    │
│                                                              │
│  Agent 3: Web search + fetch specs for topics 7-11           │
│    - Prolly tree / CRDT literature                           │
│    - IPFS gateway spec                                       │
│    - libp2p architecture overview                            │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  PARALLEL BATCH: Code Discovery (all 11 topics)              │
│                                                              │
│  Agent 4: Code scan topics 1-3                               │
│    - Find key files for CID/multihash usage patterns         │
│    - Find key files for CAR creation/parsing                 │
│    - Find key files for ucanto capability/server/client      │
│                                                              │
│  Agent 5: Code scan topics 4-6                               │
│    - Find key files for delegation/auth flows                │
│    - Find key files for content-claims/indexing              │
│    - Find key files for Filecoin pipeline                    │
│                                                              │
│  Agent 6: Code scan topics 7-11                              │
│    - Find key files for Pail operations                      │
│    - Find key files for Freeway/gateway middleware           │
│    - Find key files for encryption/KMS                       │
│    - Find key files for Go ecosystem patterns                │
│    - Find key files for libp2p usage                         │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  ALSO: Load scanner outputs as structural context            │
│    - api-surface-map.json → capability:handler:route map     │
│    - infrastructure-map.json → what infra each service uses  │
│    - product-map.json → repo roles + dependencies      │
└──────────────────────────────────────────────────────────────┘
```

**Output of 1A:** Raw materials organized per topic:
- Spec summaries (external standards)
- Key file lists with file paths
- Relevant scanner data excerpts

**Time:** Single session, highly parallel. Agents run concurrently.

### Phase 1B: Sequential Synthesis

**One topic at a time.** But much faster now because all research is done.

For each topic:

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: Spec summary + key files list from Phase 1A          │
├─────────────────────────────────────────────────────────────┤
│  1. READ key files (5-10 files, ~10-15K tokens)             │
│     Focus: type defs → constructors → handlers → tests      │
│                                                              │
│  2. EXTRACT patterns                                         │
│     Name each pattern, write copyable template               │
│     Note variations, anti-patterns, gotchas                  │
│     Use REAL code from our codebase (simplified if needed)   │
│                                                              │
│  3. DIFF against spec (only if external spec exists)         │
│     Skip for Storacha-original concepts                      │
│     For external specs: note divergences & extensions only   │
│                                                              │
│  4. WRITE memory file                                        │
│     Structure: patterns → key files → types → spec notes     │
│     Split if >300 lines into focused sub-files               │
│                                                              │
│  5. VALIDATE with test questions                             │
│     Try answering the pre-defined questions                  │
│     If answer is wrong/incomplete: iterate                   │
├─────────────────────────────────────────────────────────────┤
│  OUTPUT: memory/tech/<topic>.md (or split files)             │
└─────────────────────────────────────────────────────────────┘
```

**Grouping for efficiency:** Some topics share context and can be done in one session:
- **Session A:** Topics 1+2 (Content Addressing + CAR/UnixFS) — same libraries
- **Session B:** Topics 3+4 (ucanto + UCAN Auth) — tightly coupled
- **Session C:** Topic 5 (Content Claims) — standalone, complex
- **Session D:** Topic 6 (Filecoin Pipeline) — standalone, most complex
- **Session E:** Topics 7+8 (Pail + Gateway) — moderate complexity
- **Session F:** Topics 9+10+11 (Encryption + Go + libp2p) — can batch smaller topics

**Time:** ~6 synthesis sessions instead of 11.

### Phase 1C: Cross-Cutting & Validation

After all topic files are written:

```
┌─────────────────────────────────────────────────────────────┐
│  1. Extract CROSS-CUTTING PATTERNS                           │
│     - Error handling patterns (across JS and Go)             │
│     - Testing patterns (how tests are structured)            │
│     - Import/dependency conventions                          │
│     - Async patterns (Promises, effects, queues)             │
│     - Naming conventions                                     │
│     → Write: memory/tech/cross-cutting-patterns.md           │
│                                                              │
│  2. INTEGRATION TEST                                         │
│     For each memory file, answer 3-5 test questions:         │
│     - "How do I add a new UCAN capability?"                  │
│     - "How does a blob get from client to R2?"               │
│     - "What happens when I change a type in capabilities/?"  │
│     Score: can the file alone answer the question?           │
│     If not: iterate on that file.                            │
│                                                              │
│  3. Write MEMORY.md index                                    │
│     - Route table: "for X, read Y"                           │
│     - Top-level facts always in context                      │
│     → Write: memory/MEMORY.md                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Topic Details & Validation Questions

### Topic 1: Content Addressing Fundamentals
**Memory file:** `content-addressing.md`
**Code-first targets:** How `multiformats` is imported and used, CID construction patterns, multicodec values used, blockstore patterns
**Spec reference:** CID spec, multihash spec, IPLD data model
**Validation questions:**
1. "How do I create a CID from raw bytes in our codebase?"
2. "What hash function and codec do we use for blob storage?"
3. "How do I look up a block by CID in our blockstore?"

### Topic 2: CAR & UnixFS
**Memory file:** `car-unixfs.md`
**Code-first targets:** CAR creation/parsing patterns, UnixFS encoding, sharding logic
**Spec reference:** CAR spec (CARv1/v2), UnixFS spec
**Validation questions:**
1. "How do I pack data into a CAR file?"
2. "How does sharding work for large uploads?"
3. "How do we read a specific block from a stored CAR?"

### Topic 3: ucanto Framework
**Memory file:** `ucanto-framework.md` (may split: `ucanto-capabilities.md`, `ucanto-services.md`, `ucanto-transport.md`)
**Code-first targets:** capability() definitions, Server.provide/provideAdvanced, createService factories, connection setup, CAR transport
**Spec reference:** ucanto README, UCAN invocation spec
**Scanner leverage:** api-surface-map.json capability catalog + handler list
**Validation questions:**
1. "How do I define a new capability with typed constraints?"
2. "How do I wire a capability handler into a service?"
3. "How does a client invoke a capability on a remote service?"
4. "What is the effect system and how do fork/join work?"
5. "How do I set up a ucanto connection to another service?"

### Topic 4: UCAN Auth Model
**Memory file:** `ucan-auth-model.md`
**Code-first targets:** delegation creation, proof chain construction, attestation flow, did:mailto
**Spec reference:** UCAN spec, w3-access.md, w3-session.md, w3-account.md
**Validation questions:**
1. "How does the email-based login flow work end to end?"
2. "How do I create a delegation from a space to an agent?"
3. "How does revocation checking work?"

### Topic 5: Content Claims & Indexing
**Memory file:** `content-claims-indexing.md`
**Code-first targets:** claim types (Assert.location, Assert.index, etc.), Sharded DAG Index, IPNI publisher, indexing-service query handler
**Spec reference:** w3-index.md, our specs (assert capabilities), IPNI protocol
**Scanner leverage:** api-surface-map.json claim capabilities + indexing-service routes
**Validation questions:**
1. "How do I publish a location claim for a blob?"
2. "What is a Sharded DAG Index and how is it constructed?"
3. "How does a CID query flow through the indexing service?"
4. "How do content claims get published to IPNI?"

### Topic 6: Filecoin Pipeline
**Memory file:** `filecoin-pipeline.md` (may split: `filecoin-commp.md`, `filecoin-deal-flow.md`)
**Code-first targets:** CommP computation, FR32 padding, data-segment library, storefront→aggregator→dealer→deal-tracker handlers, inclusion proof construction
**Spec reference:** FRC-0058, Filecoin proof specs
**Scanner leverage:** api-surface-map.json filecoin capabilities
**Validation questions:**
1. "How is a CommP computed from raw data?"
2. "What is FR32 padding and when does it happen?"
3. "How does a piece move from upload through to a Filecoin deal?"
4. "What is an inclusion proof and how is it verified?"
5. "How does PDP (Provable Data Possession) work?"

### Topic 7: Pail & Data Structures
**Memory file:** `pail-data-structures.md`
**Code-first targets:** Pail put/get/del, shard splitting, CRDT merge, clock operations
**Spec reference:** Pail README (our own), prolly tree literature
**Validation questions:**
1. "How does Pail's prolly tree determine shard boundaries?"
2. "How do two Pail instances merge?"
3. "How does the Merkle clock work?"

### Topic 8: Gateway & Retrieval
**Memory file:** `gateway-retrieval.md`
**Code-first targets:** Freeway middleware stack, content serve auth delegation, blob-fetcher multipart range, locator
**Spec reference:** content-serve-auth.md, IPFS gateway spec
**Scanner leverage:** api-surface-map.json freeway entry points + middleware list
**Validation questions:**
1. "How does a gateway request flow through Freeway's middleware?"
2. "How is content serve authorization checked?"
3. "How does blob-fetcher batch byte-range requests?"

### Topic 9: Encryption & KMS
**Memory file:** `encryption-kms.md`
**Code-first targets:** KEK/DEK model, ucan-kms signing flow, encrypt-upload-client
**Spec reference:** (No external spec — Storacha-original)
**Validation questions:**
1. "How does the KEK/DEK encryption model work?"
2. "How does ucan-kms authorize signing operations?"

### Topic 10: Go Ecosystem
**Memory file:** `go-ecosystem.md`
**Code-first targets:** go-ucanto vs JS ucanto patterns, go-libstoracha capabilities, go-cid usage, go-ipld-prime patterns
**Spec reference:** (Go libraries' READMEs)
**Validation questions:**
1. "How does go-ucanto server setup differ from JS?"
2. "How do I use go-cid and go-ipld-prime to build IPLD structures?"
3. "What Go patterns does go-libstoracha follow for capabilities?"

### Topic 11: libp2p & Networking
**Memory file:** `libp2p-networking.md`
**Code-first targets:** libp2p host creation, pubsub usage, multiaddr patterns
**Spec reference:** libp2p specs
**Validation questions:**
1. "How do our Go services set up libp2p connections?"
2. "Where and why do we use pubsub?"

---

## Memory File Format (Revised)

No hard line cap. Instead: **optimize for the question "how do I do X?"**

```markdown
# [Topic]: Patterns & Reference

> Concepts: [list with P0/P1 tags]
> Key repos: [list]

## Patterns

### Pattern: [Name]
**When:** [one line]
**Template:**
```[lang]
[copyable code from our codebase]
```
**Variations:** [bullets]
**Key files:** [paths]
**Gotchas:** [bullets]

[repeat for each pattern]

## Key Files Index
| Role | File |
|------|------|
| Type definitions | ... |
| Construction | ... |
| Main handler | ... |
| Canonical test | ... |

## Key Types & Interfaces
[compact type signatures, not full files]

## Spec Notes (where external spec exists)
[brief spec baseline]
[divergences and extensions ONLY — skip conformant items]

## Design Rationale
[why this approach, known limitations, future opportunities]
```

---

## What This Procedure Does NOT Do (and why)

| Temptation | Why We Skip It |
|------------|----------------|
| Build a Neo4j knowledge graph | Adds infrastructure dependency. Scanner JSON + grep is sufficient. Deterministic AST graphs beat LLM-extracted graphs (arxiv 2601.08773), and we already have structural data from scanners. |
| Create vector embeddings of code | Stale indexing problem. Claude Code's glob/grep is just-in-time and always fresh. |
| Write comprehensive spec summaries | We're not writing a textbook. Just enough spec context to explain our divergences. |
| Document every file in every repo | 80/20 rule. The 10 key files per topic cover 80% of use cases. |
| Build custom MCP tooling now | Premature. File-based approach first. Only build tooling if we find specific repeated queries that can't be answered by file search. |

---

## Progress Tracking

### Phase 1A: Research Batch
| Topic | Spec Acquired | Code Discovered | Status |
|-------|--------------|-----------------|--------|
| 1. Content Addressing | Yes | Yes | Complete |
| 2. CAR & UnixFS | Yes | Yes | Complete |
| 3. ucanto Framework | Yes | Yes | Complete |
| 4. UCAN Auth Model | Yes | Yes | Complete |
| 5. Content Claims | Yes | Yes | Complete |
| 6. Filecoin Pipeline | Yes | Yes | Complete |
| 7. Pail & Data Structures | Yes | Yes | Complete |
| 8. Gateway & Retrieval | Yes | Yes | Complete |
| 9. Encryption & KMS | Yes | Yes | Complete |
| 10. Go Ecosystem | Yes | Yes | Complete |
| 11. libp2p & Networking | Yes | Yes | Complete |

### Phase 1B: Synthesis
| Session | Topics | Memory Files Written | Validated | Status |
|---------|--------|---------------------|-----------|--------|
| A | 1+2 | content-addressing.md, car-unixfs.md | PASS | Complete |
| B | 3+4 | ucanto-framework.md, ucan-auth-model.md | PASS | Complete |
| C | 5 | content-claims-indexing.md | PASS | Complete |
| D | 6 | filecoin-pipeline.md | PASS | Complete |
| E | 7+8 | pail-data-structures.md, gateway-retrieval.md | PASS | Complete |
| F | 9+10+11 | encryption-kms.md, go-ecosystem.md, libp2p-networking.md | PASS | Complete |

### Phase 1C: Cross-Cutting & Validation
| Task | Status |
|------|--------|
| Cross-cutting patterns file | Complete |
| Integration test (23/24 PASS, 1 PARTIAL — libp2p clarified) | Complete |
| MEMORY.md index written | Complete |

---

## Sources Consulted for This Review

- [Qodo Aware: Code-Aware Agentic AI System Approach](https://www.qodo.ai/blog/code-aware-agentic-ai-the-system-approach/)
- [Open Aware: Deep Code Research Agent](https://github.com/qodo-ai/open-aware)
- [Reliable Graph-RAG for Codebases: AST-Derived vs LLM-Extracted Graphs (arxiv 2601.08773)](https://arxiv.org/html/2601.08773)
- [Knowledge Graph Based Repository-Level Code Generation (arxiv 2505.14394)](https://arxiv.org/html/2505.14394v1)
- [Code-Graph-RAG: Monorepo Knowledge Graph](https://github.com/vitali87/code-graph-rag)
- [Arbor: Graph-Native Deterministic Code Intelligence](https://github.com/Anandb71/arbor)
- [Anthropic 2026 Agentic Coding Trends Report](https://resources.anthropic.com/2026-agentic-coding-trends-report)
- [Martin Fowler: Context Engineering for Coding Agents](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
