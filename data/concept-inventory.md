# Storacha Concept Inventory

> Ground-truth catalog of every niche concept, protocol, and data structure
> used across 82 repos. Categorized by learning priority for Claude Code.

## Priority Legend

- **P0 — CRITICAL**: Storacha-specific or heavily customized. I will get this WRONG without deep study. Must extract patterns from code.
- **P1 — HIGH**: Niche protocol/format. I have partial knowledge but Storacha uses it in specific ways. Need to study both spec and implementation.
- **P2 — MEDIUM**: Known technology used in domain-specific ways. I understand the concept but need to learn Storacha's patterns.
- **P3 — LOW**: Well-understood technology. Standard usage, minimal study needed.

---

## 1. UCAN & Authorization Layer

### P0 — CRITICAL (Storacha-specific)

| Concept | What It Is | Where Defined | Where Implemented | Why P0 |
|---------|-----------|---------------|-------------------|--------|
| **ucanto RPC framework** | Full UCAN-based RPC: capability definition, server routing, client invocation, validation | `ucanto/` | `upload-service/`, `content-claims/`, `w3infra/`, `freeway/` | Custom framework. Not a standard. Pattern recognition essential. |
| **Capability definition pattern** | `capability({ can, with, nb, derives })` | `upload-service/packages/capabilities/src/` | Same | 175 capabilities. Must know the pattern cold. |
| **Service handler wiring** | `Server.provide()` / `Server.provideAdvanced()` + service factories | `upload-service/packages/upload-api/src/` | Same + `content-claims/`, `w3filecoin-infra/` | Core development pattern. |
| **Effect system (fork/join)** | Async effects returned from invocations, enabling pipelines | `w3-filecoin.md` spec | `upload-service/packages/filecoin-api/` | Unique to ucanto. Not in any standard lib. |
| **Delegation chain & proof resolution** | How delegation proofs are created, chained, validated | `w3-access.md`, `w3-session.md` | `ucanto/packages/validator/`, `upload-service/packages/access-client/` | Authorization model is non-standard. |
| **Attestation signatures** | Zero-length VarSig + DKIM-based auth for did:mailto | `w3-account.md`, `w3-session.md` | `upload-service/packages/upload-api/src/access/` | Completely custom crypto pattern. |
| **go-ucanto** | Go port of ucanto with different idioms | `go-ucanto/` | `indexing-service/`, `delegator/`, `piri/`, `guppy/` | Different patterns than JS version. |

### P1 — HIGH (Niche protocol, Storacha-specific usage)

| Concept | What It Is | Spec | Implementation | Why P1 |
|---------|-----------|------|----------------|--------|
| **UCAN (spec)** | Capability-based auth tokens | UCAN spec (external) | `ucanto/` | I know the concept but not the wire format details. |
| **DID methods (did:key, did:web, did:mailto)** | Decentralized identifiers | W3C DID Core, `did-mailto.md` | `ucanto/packages/principal/`, `upload-service/packages/did-mailto/` | did:mailto is custom. did:key/did:web are standard but usage patterns matter. |
| **Invocation/Receipt model** | Request = invocation, response = receipt with CID | UCAN Invocation spec | `ucanto/packages/core/` | Wire format is specific. |
| **Revocation protocol** | How UCANs are revoked and checked | `w3-revocations-check.md` | `upload-service/packages/upload-api/`, `w3infra/` | Custom endpoint + protocol. |

---

## 2. Content Addressing & Data Model

### P0 — CRITICAL

| Concept | What It Is | Where Defined | Where Implemented | Why P0 |
|---------|-----------|---------------|-------------------|--------|
| **Sharded DAG Index** | Index mapping content DAG blocks to blob slices (digest, offset, length) | `w3-index.md` | `upload-service/packages/blob-index/` | Custom data structure. Core to retrieval. |
| **Content Claims protocol** | Signed assertions about content: location, inclusion, index, relation, equals, partition | specs + `content-claims/` | `content-claims/packages/core/`, `indexing-service/` | Completely custom protocol. |
| **Blob allocation flow** | Space requests allocation → provider reserves → client PUTs via HTTP → provider confirms | `w3-blob.md` | `upload-service/packages/upload-api/src/blob/` | Multi-step protocol with receipts. |
| **Location Commitment** | Signed assertion that a multihash can be found at an HTTP URL + byte range | `w3-blob.md` | `content-claims/`, `blob-fetcher/` | Custom concept linking content addressing to HTTP. |

### P1 — HIGH

| Concept | What It Is | Packages | Why P1 |
|---------|-----------|----------|--------|
| **CID (Content Identifier)** | Self-describing content address: multicodec + multihash + version | `multiformats` (JS), `go-cid` (Go) | I know CIDs conceptually but need to know construction details, codec codes, hash functions used. |
| **Multihash** | Self-describing hash: varint code + varint length + digest bytes | `multiformats`, `go-multihash` | Need to know which hash functions Storacha uses (SHA2-256 primarily) and the binary format. |
| **Multicodec** | Varint code identifying data format (dag-cbor=0x71, dag-pb=0x70, raw=0x55, etc.) | `multiformats`, `go-multicodec` | Need to know the specific codes used across the codebase. |
| **IPLD data model** | Kinds: null, bool, int, float, string, bytes, list, map, link. Everything is a typed DAG node. | `@ipld/dag-cbor`, `go-ipld-prime` | Need to understand how Storacha constructs IPLD structures. |
| **DAG-CBOR** | Canonical deterministic CBOR encoding for IPLD. Links encoded as CBOR tag 42. | `@ipld/dag-cbor`, `go-ipld-prime` | Primary encoding format. Must understand encoding rules. |
| **DAG-JSON** | JSON encoding for IPLD with `{"/": "bafy..."}` link representation. | `@ipld/dag-json` | Used in APIs and debugging. |
| **DAG-PB** | Legacy protobuf-based IPLD codec from IPFS. | `@ipld/dag-pb`, `go-codec-dagpb` | Used for UnixFS. Must understand for legacy compatibility. |
| **Block** | A CID + bytes pair. The atomic unit of content-addressed storage. | `multiformats`, blockstore packages | Fundamental to all operations. |
| **Blockstore** | Key-value store mapping CID→Block bytes. | `blockstore-core`, `go-ipfs-blockstore` | Used throughout. |

### P2 — MEDIUM

| Concept | What It Is | Why P2 |
|---------|-----------|--------|
| **CAR (Content Addressable aRchive)** | File format: header (roots) + concatenated blocks. CARv1 and CARv2. | I know the format but need to know Storacha's CAR packing/unpacking patterns. |
| **UnixFS** | IPFS file/directory encoding on top of DAG-PB. Chunking + Merkle tree. | Need to know chunker settings, tree shape Storacha uses. |
| **Varint** | Variable-length integer encoding (unsigned LEB128). | Used pervasively in multiformats. Simple but need to recognize it. |
| **Multibase** | Self-describing base encoding (base32, base58btc, base64url). | Need to know which bases Storacha uses where. |

---

## 3. Filecoin Integration Pipeline

### P0 — CRITICAL

| Concept | What It Is | Where Defined | Where Implemented | Why P0 |
|---------|-----------|---------------|-------------------|--------|
| **CommP (Piece Commitment)** | SHA256-trunc254-padded binary tree hash over FR32-padded data. THE Filecoin piece identifier. | Filecoin specs, FRC-0058 | `data-segment/`, `fr32-sha2-256-...`, `go-fil-commp-hashhash/` | Extremely niche. Complex math. Multiple repos implement this. |
| **FR32 padding** | Filecoin Reed-Solomon 32-byte padding: every 254 bits → 256 bits (2 zero bits injected per 254). | Filecoin specs | `fr32-sha2-256-trunc254-padded-binary-tree-multihash/`, `data-segment/` | Custom binary encoding. Easy to get wrong. |
| **Data Aggregation (FRC-0058)** | Combining multiple pieces into an aggregate with inclusion proofs. Merkle tree of piece commitments. | `w3-filecoin.md`, FRC-0058 | `upload-service/packages/filecoin-api/`, `w3filecoin-infra/` | Storacha's core Filecoin pipeline. |
| **Storefront → Aggregator → Dealer → DealTracker pipeline** | 4-service async pipeline for getting data into Filecoin deals | `w3-filecoin.md` | `upload-service/packages/filecoin-api/src/{storefront,aggregator,dealer,deal-tracker}/` | Core business logic. Must understand each stage. |
| **PDP (Provable Data Possession)** | Proof system for verifying storage providers actually hold data | `w3-filecoin.md`, Filecoin specs | `piri/`, `filecoin-services/service_contracts/` | New capability, Solidity contracts involved. |
| **Inclusion Proof** | Merkle proof that a piece exists within an aggregate at a specific offset | `w3-filecoin.md` | `upload-service/packages/filecoin-api/` | Custom proof structure. |

### P1 — HIGH

| Concept | What It Is | Packages | Why P1 |
|---------|-----------|----------|--------|
| **CommD (Data Commitment)** | Unsealed sector commitment hash. Related to CommP but for unsealed data. | `go-fil-commcid`, Filecoin specs | Need to understand relationship to CommP. |
| **Piece CID** | CID with fil-commitment-unsealed codec (0xf101) wrapping CommP multihash. | `go-fil-commcid`, `data-segment/` | Specific CID construction pattern. |
| **Filecoin deal lifecycle** | propose → publish → activate → expire/slash | Lotus, `filecoin-spade-client/` | Need to understand state machine. |
| **SPADE** | Deal-making system Storacha uses for Filecoin storage | `spade/`, `spade-agent/`, `filecoin-spade-client/` | Storacha-specific integration. |
| **Sector** | Filecoin storage unit (32GiB or 64GiB). Aggregate must fit within sector. | Filecoin specs | Constraint on aggregation. |

### P2 — MEDIUM

| Concept | What It Is | Why P2 |
|---------|-----------|--------|
| **Filecoin actors/state types** | On-chain state machine for deals, sectors, payments | Used transitively. Need basic understanding. |
| **go-data-segment** | Go implementation of data segment operations | Dependency of several Go repos. |

---

## 4. IPNI & Content Discovery

### P0 — CRITICAL

| Concept | What It Is | Where Defined | Where Implemented | Why P0 |
|---------|-----------|---------------|-------------------|--------|
| **IPNI (InterPlanetary Network Indexer)** | Network service for discovering which providers hold which content | IPNI specs | `indexing-service/`, `ipni-publisher/`, `storetheindex/` | Core to Storacha retrieval. |
| **Provider Advertisement** | Signed announcement to IPNI that a provider holds certain content | IPNI specs, `go-libipni` | `indexing-service/`, `ipni-publisher/`, `go-libstoracha/` | Must understand to work on indexing. |
| **Content Claims → IPNI bridge** | How Storacha's content claims get published as IPNI advertisements | Custom | `indexing-service/`, `go-libstoracha/` | Completely custom integration. |

### P1 — HIGH

| Concept | What It Is | Packages | Why P1 |
|---------|-----------|----------|--------|
| **EntryChunk** | IPNI data structure containing multihash entries for an advertisement | `go-libipni` | Need to understand for indexing work. |
| **Metadata** | IPNI metadata describing how to retrieve content from a provider | `go-libipni`, `go-libstoracha/` | Custom metadata format for Storacha. |
| **Content Routing** | Protocol for finding providers of content by CID | Delegated routing specs | Storacha implements custom content routing via claims. |

---

## 5. Pail & Distributed Data Structures

### P0 — CRITICAL

| Concept | What It Is | Where Defined | Where Implemented | Why P0 |
|---------|-----------|---------------|-------------------|--------|
| **Pail** | DAG-based key-value store using prolly trees. CRDT-mergeable. | `pail/` README | `pail/`, `go-pail/` | Completely custom data structure. Used for sharded storage. |
| **ShardedDAG** | A DAG split across multiple shards, each a separate blob/CAR | Various | `upload-service/packages/blob-index/` | Core storage model. |
| **ShardBlock / ShardEntry** | Pail internal: entries within a shard of the prolly tree | `pail/` | `pail/src/` | Must understand for any Pail work. |

### P1 — HIGH

| Concept | What It Is | Why P1 |
|---------|-----------|--------|
| **Prolly Tree** | Probabilistic B-tree with content-defined boundaries for deterministic splits | Foundational to Pail. Need to understand split/merge behavior. |
| **Merkle Clock** | Partially ordered event log using Merkle DAG links for causality | Used in `w3clock/`, `pail/src/clock/`. Custom CRDT primitive. |
| **CRDT (Conflict-free Replicated Data Type)** | Data structure that can be merged without coordination | Pail is a CRDT. Need to understand merge semantics. |

---

## 6. Encryption & Key Management

### P0 — CRITICAL

| Concept | What It Is | Where Implemented | Why P0 |
|---------|-----------|-------------------|--------|
| **Storacha encryption model** | KEK/DEK pattern: key encryption keys protect per-content data encryption keys | `upload-service/packages/encrypt-upload-client/` | Custom architecture. |
| **KMS integration (ucan-kms)** | UCAN-authorized key operations via Google Cloud KMS + Cloudflare Worker | `ucan-kms/` | Custom service bridging UCAN auth to cloud KMS. |

### P1 — HIGH

| Concept | What It Is | Why P1 |
|---------|-----------|--------|
| **ed25519** | Signature algorithm used for did:key principals | Standard but need to know where/how used. |
| **P-256 / ECDH** | Key agreement for encrypted content sharing | Used in access-client crypto. |
| **AES-GCM** | Symmetric encryption for content | Used in encrypt-upload-client. |

---

## 7. Networking & Transport

### P1 — HIGH

| Concept | What It Is | Packages | Why P1 |
|---------|-----------|----------|--------|
| **libp2p** | Modular P2P networking stack | `go-libp2p`, `@libp2p/*` | Used in Go services. Need to understand connection model. |
| **Bitswap** | Block exchange protocol in IPFS | `dagula/`, `go-libp2p` | Used for direct block transfer. |
| **Multiaddr** | Self-describing network address format | `go-multiaddr`, `@multiformats/multiaddr` | Used throughout Go code. |
| **Noise protocol** | Encryption for libp2p connections | `@chainsafe/libp2p-noise` | Transport security. |

### P2 — MEDIUM

| Concept | What It Is | Why P2 |
|---------|-----------|--------|
| **QUIC** | UDP-based transport used by libp2p | Used in Go services. Standard protocol. |
| **WebRTC / WebTransport** | Browser-compatible P2P transports | Used in some libp2p configs. |
| **GraphSync** | IPLD-aware data transfer protocol | Used in Filecoin data transfer. |

---

## 8. Gateway & Retrieval

### P0 — CRITICAL

| Concept | What It Is | Where Implemented | Why P0 |
|---------|-----------|-------------------|--------|
| **Freeway middleware stack** | Layered middleware for UCAN-authorized IPFS gateway | `freeway/src/` | 15+ composable middlewares. Core retrieval path. |
| **Content serve authorization** | UCAN-based gateway access: delegated rights to serve content from a space | `content-serve-auth.md` spec, `freeway/` | Custom auth model for gateways. |
| **Blob fetcher with batching** | Fetches blobs using multipart byte-range requests, batches for efficiency | `blob-fetcher/` | Custom retrieval optimization. |

### P1 — HIGH

| Concept | What It Is | Why P1 |
|---------|-----------|--------|
| **IPFS HTTP Gateway spec** | Standard HTTP interface for IPFS content retrieval | Storacha implements with custom auth on top. |
| **Multipart byte-range** | HTTP technique for fetching multiple byte ranges in one request | Used in blob-fetcher for efficient retrieval. |
| **Carpark** | R2 bucket storing CAR files, accessed via public URL | Infrastructure concept specific to Storacha. |

---

## 9. Service Architecture Patterns

### P0 — CRITICAL

| Concept | What It Is | Where | Why P0 |
|---------|-----------|-------|--------|
| **ucanto connection model** | `connect({ id, codec: CAR.outbound, channel: HTTP.open({ url }) })` | Throughout JS services | Must know this pattern for any inter-service work. |
| **CAR-encoded RPC** | All ucanto RPCs are encoded as CAR files over HTTP POST | `ucanto/packages/transport/` | Unusual transport. Need to understand for debugging. |
| **Wrangler service bindings** | CF Worker-to-Worker direct calls via bindings | `reads/`, `w3link/`, `freeway/` | CF-specific pattern used extensively. |
| **SST infrastructure-as-code** | AWS infrastructure defined in SST stacks | `w3infra/`, `content-claims/`, `w3filecoin-infra/` | Need to understand for infra changes. |
| **Queue-based async pipelines** | CF Queues / SQS for async service communication | `freeway/` → `egress-consumer/`, Filecoin pipeline | Core architectural pattern. |

### P2 — MEDIUM

| Concept | What It Is | Why P2 |
|---------|-----------|--------|
| **Cloudflare Workers** | Serverless JS runtime | Well-known but need to know Storacha's patterns. |
| **Cloudflare D1** | SQLite-at-edge database | Standard CF product, specific usage matters. |
| **Cloudflare R2** | S3-compatible object storage | Standard but need to know bucket layout. |
| **DynamoDB** | AWS NoSQL database | Standard. Need to know table schemas. |
| **Durable Objects** | Stateful CF Workers | Used for specific features. |

---

## 10. Storacha-Internal Custom Components

### P0 — CRITICAL (All unique to Storacha)

| Component | What It Is | Repo |
|-----------|-----------|------|
| **go-libstoracha** | Go capabilities library: UCAN types, content claims, IPNI integration | `go-libstoracha/` |
| **piri** | Next-gen storage node (Go): PDP, Filecoin deals, block storage | `piri/` |
| **delegator** | Go service for creating UCAN delegations | `delegator/` |
| **piri-signing-service** | Signing service for piri operations | `piri-signing-service/` |
| **etracker** | Event/receipt tracking service (Go) | `etracker/` |
| **storoku** | Deployment tooling for Storacha infrastructure | `storoku/` |
| **forgectl** | Forge control tooling | `forgectl/` |
| **filecoin-services** | Solidity smart contracts + Go services for Filecoin integration | `filecoin-services/` |

---

## Summary: Learning Priority Distribution

| Priority | Count | Description |
|----------|-------|-------------|
| **P0 — CRITICAL** | ~35 concepts | Will get WRONG without code study. Must extract patterns. |
| **P1 — HIGH** | ~30 concepts | Partial knowledge. Need spec + implementation study. |
| **P2 — MEDIUM** | ~20 concepts | Known tech, need Storacha-specific patterns. |
| **P3 — LOW** | ~15 concepts | Standard. Minimal study. |

## Dependency Ecosystem Size

| Ecosystem | JS Packages | Go Modules | Total |
|-----------|------------|------------|-------|
| UCAN/ucanto | 9 | 2 | 11 |
| IPLD/DAG | 7 | 8 | 15 |
| Multiformats | 8 | 10 | 18 |
| Filecoin | 6 | 25+ | 31+ |
| IPFS core | 8 | 20+ | 28+ |
| libp2p | 13 | 15+ | 28+ |
| IPNI | 2 | 4 | 6 |
| Crypto | 7 | 5 | 12 |
| **Total niche deps** | **~60** | **~90+** | **~150+** |
