# Storacha Codebase Knowledge Index

## Quick Routing Table

| If you need to... | Read this file |
|---|---|
| Create/parse CIDs, work with multihash/multicodec | `memory/tech/content-addressing.md` |
| Create/parse CAR files, encode UnixFS, shard uploads | `memory/tech/car-unixfs.md` |
| Define capabilities, wire handlers, create servers (JS) | `memory/tech/ucanto-framework.md` |
| Understand auth flow, delegations, sessions, did:mailto | `memory/tech/ucan-auth-model.md` |
| Work with content claims, ShardedDAGIndex, IPNI | `memory/tech/content-claims-indexing.md` |
| Understand Filecoin pipeline, CommP, FR32, PDP | `memory/tech/filecoin-pipeline.md` |
| Work with Pail KV store, CRDT merge, Merkle clock | `memory/tech/pail-data-structures.md` |
| Understand gateway retrieval, Freeway middleware, blob-fetcher | `memory/tech/gateway-retrieval.md` |
| Work with encryption, KMS, ECDH key agreement | `memory/tech/encryption-kms.md` |
| Build Go services, go-ucanto, go-libstoracha | `memory/tech/go-ecosystem.md` |
| Understand libp2p usage, GossipSub, multiaddr | `memory/tech/libp2p-networking.md` |
| Error handling, testing, naming, async patterns | `memory/tech/cross-cutting-patterns.md` |
| Trace: file upload end-to-end (7 steps) | `memory/flows/upload-flow.md` |
| Trace: content retrieval via gateway (26 middlewares) | `memory/flows/retrieval-flow.md` |
| Trace: auth, login, delegation chains | `memory/flows/auth-flow.md` |
| Trace: Filecoin deal lifecycle (JS + Go pipelines) | `memory/flows/filecoin-deal-flow.md` |
| Trace: egress tracking → billing | `memory/flows/egress-tracking-flow.md` |
| Map: which specs are implemented, divergences | `memory/architecture/spec-implementation-map.md` |
| Shared packages, blast radius, version coupling | `memory/architecture/shared-packages.md` |
| Infrastructure: SST, DynamoDB schemas, R2, Wrangler, queues | `memory/architecture/infrastructure-decisions.md` |

## Top-Level Architecture Facts

- **82 repos** under github.com/storacha (previously web3-storage)
- **Two languages**: JS/TS (ucanto, w3up, upload-service, freeway) and Go (piri, indexing-service, go-ucanto, go-libstoracha)
- **UCAN-based RPC**: All service communication uses ucanto (capability invocations over CAR-encoded HTTP)
- **Content-addressed storage**: Data stored as CAR shards in R2/S3, indexed by ShardedDAGIndex, discoverable via IPNI
- **Two Filecoin paths**: JS pipeline (Spade deals) and Go pipeline (PDP/Ethereum proofs)
- **Package migration**: `@web3-storage/*` → `@storacha/*` in progress; `@ucanto/*` stays

## Key Service Map

| Service | Repo | Language | Role |
|---------|------|----------|------|
| Upload API | upload-service / w3up | JS | Blob/upload/index handling |
| Freeway | freeway | JS (CF Worker) | IPFS gateway with UCAN auth |
| UCAN KMS | ucan-kms | JS (CF Worker) | Encryption key management |
| Indexing Service | indexing-service | Go | Content routing (IPNI + claims) |
| Piri | piri | Go | Storage node (PDP proofs) |
| Content Claims | content-claims | JS | Claim storage and serving |

## Scanner Data Available

Pre-computed structural data in `data/`:
- `api-surface-map.json` — 175 UCAN capabilities, 231 service graph edges, handlers, routes
- `infrastructure-map.json` — DynamoDB, S3/R2, SQS, 57 SQL schemas across 32 repos
- `product-map.json` — 82 repos grouped into 15 products with roles, deps, tech stack

Scanners: `scripts/scan_api_surface.py`, `scripts/scan_infra.py`, `scripts/scan_products.py`

## Slash Commands

| Command | What It Does |
|---------|-------------|
| `/trace <flow>` | Load end-to-end flow trace (upload, retrieval, auth, filecoin, egress) |
| `/impact <pkg-or-cap>` | Assess blast radius of a change to a package or capability |
| `/spec <spec-name>` | Show spec-to-implementation mapping and divergences |
| `/new-capability` | Step-by-step guide for adding a UCAN capability |

## Query Tool (Layer 5)

For cross-cutting queries correlating capabilities, repos, infra, and service graphs:
```bash
python aidev/tools/query.py <command> [args]
```
Commands: `capability`, `impact`, `infra`, `graph`, `product`, `repo`. Run without args for usage.

## Research Data

Raw research files (spec + code discovery) in `research/raw/research-*.md` — useful for deep dives beyond what the synthesized files cover.
