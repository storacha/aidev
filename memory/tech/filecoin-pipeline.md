<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Filecoin Pipeline: Patterns & Reference

> **TL;DR:** Two parallel pipelines for Filecoin storage. JS pipeline (w3up): `filecoin/offer` -> storefront -> aggregator -> dealer -> deal-tracker, using Spade for traditional Filecoin deals. Go pipeline (Piri): PDP-based using Ethereum smart contracts for Provable Data Possession proofs (hot storage). Both compute CommP (FR32-padded SHA2-256 binary Merkle tree, multicodec 0x1011). Pieces are aggregated into ~128MB+ aggregates with inclusion proofs per FRC-0058.

> Concepts: CommP/Piece commitment (P0), FR32 padding (P0), data aggregation (P0), inclusion proofs (P0), storefront→aggregator→dealer→deal-tracker (P0), PDP (P0)
> Key repos: w3up (filecoin-api, capabilities), data-segment, fr32-sha2-256-...-multihash, piri

## Pipeline Overview

```
           JS Pipeline (w3up)                         Go Pipeline (Piri)

  filecoin/offer (agent)                    blob/accept
       │                                         │
       ├→ filecoin/submit (storefront)           ├→ CommP calculation (async queue)
       │     └→ piece/offer (aggregator)         ├→ assert/location claim
       │           └→ piece/accept               └→ pdp/accept (async)
       │                 └→ aggregate/offer                │
       │                       └→ aggregate/accept         ├→ aggregation into proof set
       │                             └→ deal/info          └→ Ethereum smart contract
       │                                                        (challenge/prove)
       └→ filecoin/accept (follows receipt chain back)
              returns: { piece, aggregate, inclusion proof, deal info }
```

**Two pipelines exist:**
1. **JS pipeline** (w3up/filecoin-api): Storefront→Aggregator→Dealer→Deal-Tracker using Filecoin deal-making via Spade
2. **Go pipeline** (Piri): PDP-based — uses Ethereum smart contracts for Provable Data Possession proofs

## Core Concepts

### CommP (Piece Commitment)
A content-addressed commitment to a piece of data, computed by:
1. **FR32 pad** the raw data (insert 2 zero bits per 254 data bits)
2. **Zero-pad** to the next power-of-2 piece size
3. Build a **binary Merkle tree** over the padded data (SHA2-256-trunc254)
4. The root hash IS the CommP

**Multicodec code:** `0x1011` (`fr32-sha2-256-trunc254-padded-binary-tree`)
**CID format:** CIDv1 with raw codec (0x55) + CommP multihash

### PieceLink Type
```js
const FR32_SHA2_256_TRUNC254_PADDED_BINARY_TREE = 0x1011
const PieceLink = Schema.link({
  code: 0x55,          // raw codec
  version: 1,
  multihash: { code: 0x1011 },
})
```

### Inclusion Proof
A pair `[tree_proof, index_proof]` proving a piece exists within an aggregate:
- **tree_proof**: Merkle path from piece to aggregate root
- **index_proof**: Proves the piece's position within the aggregate's index

## Patterns

### Pattern: Compute a CommP from data (JS)
**When:** Computing a piece commitment for filecoin storage
**Template:**
```js
import * as Hasher from 'fr32-sha2-256-trunc254-padded-binary-tree-multihash'

// One-shot:
const digest = Hasher.digest(payloadBytes)  // → PieceDigest
const pieceCID = Link.create(0x55, digest)

// Streaming (for large data):
const hasher = Hasher.create()
hasher.write(chunk1)
hasher.write(chunk2)
const digest = hasher.digest()
```
**Key files:** `data-segment/src/multihash.js`, `fr32-sha2-256-trunc254-padded-binary-tree-multihash/src/hasher.rs`
**Gotchas:**
- JS implementation exists but Rust/WASM version is used for performance
- Digest includes: `[padding_varint, height_byte, 32_byte_root]`
- Multicodec code `0x1011` must be in the multihash prefix

### Pattern: FR32 padding
**When:** Preparing data for Filecoin proof-of-replication
**Template:**
```js
import { pad, toZeroPaddedSize } from 'data-segment/src/fr32.js'

// FR32 inserts 2 zero bits per 254 data bits → 254 data bits become 256 bits
const paddedSize = toZeroPaddedSize(payloadSize)  // next power-of-2 aligned
const padded = pad(sourceBytes)  // bit-level manipulation
```
**Key files:** `data-segment/src/fr32.js`
**Gotchas:**
- Works on 127-byte "quads" (4 groups of ~31 bytes with 1-byte shims)
- Bit manipulation: shifts and masks to insert 2 zero bits at 254-bit boundaries
- `output[writeOffset + 31] &= 0b00111111` — the 2-bit shim

### Pattern: Start the Filecoin pipeline (filecoin/offer)
**When:** Agent offers a piece for Filecoin storage
**Template:**
```js
const receipt = await StorefrontCaps.filecoinOffer
  .invoke({
    issuer: agent,
    audience: storefrontDID,
    with: agent.did(),
    nb: {
      content: blobCID,   // CID of the content/CAR
      piece: pieceCID,    // CommP piece CID
    },
    proofs: [delegation],
  })
  .execute(connection)
// receipt.out.ok = { piece }
// receipt.fx = { fork: [submitTask], join: acceptTask }
```
**Key files:** `w3up/packages/filecoin-api/src/storefront/service.js:21-78`

### Pattern: Handle filecoin/offer (storefront)
**When:** Storefront receives a piece offer from an agent
**Template:**
```js
export const filecoinOffer = async ({ capability }, context) => {
  const { piece, content } = capability.nb

  // Check if piece already known
  const hasRes = await context.pieceStore.has({ piece })
  if (!hasRes.ok) {
    // Queue for processing
    await context.filecoinSubmitQueue.add({ piece, content, group })
  }

  // Create chained effects: submit → accept
  const [submitfx, acceptfx] = await Promise.all([
    StorefrontCaps.filecoinSubmit.invoke({...}).delegate(),
    StorefrontCaps.filecoinAccept.invoke({...}).delegate(),
  ])

  return Server.ok({ piece })
    .fork(submitfx.link())    // fork: submit runs async
    .join(acceptfx.link())    // join: accept waits for submit chain to complete
}
```
**Key files:** `w3up/packages/filecoin-api/src/storefront/service.js`
**Gotchas:**
- The `fork/join` effect chain is the core pipeline mechanism — each handler creates effects that chain to the next step
- `group` parameter identifies the storage service provider

### Pattern: Create equals claim (piece↔content)
**When:** After piece computation, link content CID to piece CID
**Template:**
```js
await Assert.equals
  .invoke({
    issuer: claimsService.invocationConfig.issuer,
    audience: claimsService.invocationConfig.audience,
    with: claimsService.invocationConfig.with,
    nb: {
      content: record.content,    // blob/CAR CID
      equals: record.piece,       // CommP piece CID
    },
    expiration: Infinity,
    proofs: claimsService.invocationConfig.proofs,
  })
  .execute(claimsService.connection)
```
**Key files:** `w3up/packages/filecoin-api/src/storefront/events.js:131-154`

### Pattern: PDP integration in blob/accept (Go)
**When:** Piri storage node accepts a blob with PDP enabled
**Template:**
```go
// 1. Enqueue CommP calculation
s.PDP().CommpCalculate().Enqueue(ctx, req.Blob.Digest)

// 2. Create pdp/accept invocation (resolves when aggregation completes)
pieceAccept, _ := pdp_cap.Accept.Invoke(
    s.ID(), s.ID(), s.ID().DID().String(),
    pdp_cap.AcceptCaveats{Blob: req.Blob.Digest},
    delegation.WithNoExpiration(),
)

// 3. Create location claim
claim, _ := assert.Location.Delegate(s.ID(), req.Space, s.ID().DID().String(),
    assert.LocationCaveats{...}, delegation.WithNoExpiration())

// 4. Return with effects
return result.Ok(blob.AcceptOk{Site: claim.Link(), PDP: &pdpLink}),
    fx.NewEffects(fx.WithFork(
        fx.FromInvocation(claim),
        fx.FromInvocation(pieceAccept),
    )), nil
```
**Key files:** `piri/pkg/service/storage/handlers/blob/accept.go`, `piri/pkg/service/storage/ucan/blob_accept.go`

### Pattern: Build an aggregate from pieces (Go)
**When:** Aggregating multiple pieces into one Filecoin deal
**Template:**
```go
import "github.com/storacha/piri/pkg/pdp/aggregation/aggregator"

// Pieces must be sorted largest to smallest
aggregate, err := aggregator.NewAggregate(pieceLinks)
// Builds a stack-based Merkle tree with zero-padding for power-of-2 alignment
// Returns: aggregate CommP + inclusion proofs for each piece
```
**Key files:** `piri/pkg/pdp/aggregation/aggregator/aggregate.go`
**Gotchas:**
- Pieces MUST be sorted from largest to smallest
- Each piece must have paddedSize >= 128 bytes
- The aggregate uses stack-based tree construction with zero-padding

## Pipeline Capability Chain

```
filecoin/offer → filecoin/submit → piece/offer → piece/accept → aggregate/offer → aggregate/accept → deal/info
   (agent)         (storefront)     (aggregator)  (aggregator)     (dealer)          (dealer)      (deal-tracker)
```

Each handler:
1. Does its work (queue, store, verify)
2. Returns `Server.ok({...}).fork(nextStep).join(completionStep)` or `.join(nextStep)`
3. The receipt chain enables `filecoin/accept` to trace back through all steps

## Key Files Index

| Role | File |
|------|------|
| PieceLink type | `w3up/packages/capabilities/src/filecoin/lib.js` |
| filecoin/* capabilities | `w3up/packages/capabilities/src/filecoin/storefront.js` |
| piece/* capabilities | `w3up/packages/capabilities/src/filecoin/aggregator.js` |
| aggregate/* capabilities | `w3up/packages/capabilities/src/filecoin/dealer.js` |
| deal/* capabilities | `w3up/packages/capabilities/src/filecoin/deal-tracker.js` |
| Storefront handlers | `w3up/packages/filecoin-api/src/storefront/service.js` |
| Aggregator handlers | `w3up/packages/filecoin-api/src/aggregator/service.js` |
| Dealer handlers | `w3up/packages/filecoin-api/src/dealer/service.js` |
| Deal-tracker handlers | `w3up/packages/filecoin-api/src/deal-tracker/service.js` |
| Storefront events | `w3up/packages/filecoin-api/src/storefront/events.js` |
| CommP hasher (JS) | `data-segment/src/multihash.js` |
| CommP hasher (Rust/WASM) | `fr32-sha2-256-trunc254-padded-binary-tree-multihash/src/hasher.rs` |
| FR32 padding | `data-segment/src/fr32.js` |
| Inclusion proofs | `data-segment/src/inclusion.js` |
| Piece types (JS) | `data-segment/src/piece.js` |
| Go aggregation | `piri/pkg/pdp/aggregation/aggregator/aggregate.go` |
| Go CommP calculator | `piri/pkg/pdp/aggregation/commp/commp.go` |
| PDP types (Go) | `piri/pkg/pdp/types/api.go` |
| PDP blob/accept (Go) | `piri/pkg/service/storage/handlers/blob/accept.go` |
| PDP info (Go) | `piri/pkg/service/storage/ucan/pdp_info.go` |
| pdp/* capabilities (Go) | `go-libstoracha/capabilities/pdp/` |
| pdp/* capabilities (JS) | `upload-service/packages/capabilities/src/pdp.js` |

## Spec Notes

**FR32 padding:** Filecoin proofs require data in "field representation" — each 254 bits get 2 zero bits appended to fit in a 256-bit field element. Ratio: 127 payload bytes → 128 padded bytes.

**FRC-0058 (Verifiable Data Aggregation):** Defines how multiple data pieces are combined into a single deal:
- Data segments are aligned to power-of-2 boundaries
- Inclusion proof: tree path (piece → aggregate root) + index path (position in segment)
- Aggregate CommP = Merkle root over all zero-padded, aligned piece CommPs

**PDP (Provable Data Possession):** Piri's approach for "hot" data storage:
- Uses Ethereum smart contracts for proof sets and challenge windows
- Storage node must respond to challenges by generating proofs
- Replaces Filecoin sealing for data that needs to remain immediately retrievable

## P1 Details: CommD vs CommP

CommP and CommD are **functionally identical** — they are just different names:
- **CommP** = Commitment to Piece (Filecoin terminology)
- **CommD** = Data Commitment (alternative Filecoin spec term)
- Both refer to the same 32-byte unsealed commitment value

The `go-fil-commp-hashhash` library calculates this from raw bytestreams:
```go
// Package commp — Filecoin Unsealed Commitment (commP/commD)
// MaxLayers = 31 (log2(64 GiB / 32))
// MaxPieceSize = 2^36 = 64 GiB
```

**Key files:** `go-fil-commp-hashhash/commp.go`

## P1 Details: Piece CID Construction

Two multicodec encodings depending on context:

| Context | Multicodec | Multihash Code | Usage |
|---------|-----------|----------------|-------|
| Raw/aggregate PieceLink | 0x55 (raw) | 0x1011 (fr32-sha2-256-trunc254-padded-binary-tree) | Modern FRC58 format |
| Legacy PieceCID | 0xf101 (fil-commitment-unsealed) | 0x1012 (sha256-trunc254-padded) | Filecoin deal compatibility |

**Construction flow (modern):**
```
Raw CommP (32 bytes) → Multihash(0x1011, digest) → CID(v1, 0x55, multihash)
```

**Conversion to legacy (via go-fil-commcid):**
```go
commCid, err := commcid.DataCommitmentV1ToCID(rawCommP)
// → CID(v1, 0xf101, Multihash(0x1012, rawCommP))
```

**Tree height encoding:** First byte of multihash digest = tree height.
`PieceSize = 2^(5 + height)` bytes.

**Key files:** `data-segment/src/piece.js`, `data-segment/src/multihash.js`, `data-segment/src/digest.js`

## P1 Details: SPADE Deal-Making

SPADE (Storage Provider Aggregation Deal Engine) is a REST API for Filecoin deal-making used by the JS pipeline:

```
SpadeClient API:
  GET  /sp/pending_proposals    → Current deal proposals
  GET  /sp/eligible_pieces      → Pieces ready for deals (10s cache)
  POST /sp/invoke               → Reserve a piece (call=reserve_piece&piece_cid=X)
  GET  /sp/piece_manifest       → FRC58 aggregate manifest
```

**Key types:**
```go
type DealProposal struct {
    ProposalID, PieceCid string
    PieceSize            int64
    HoursRemaining       int
    StartEpoch           int64
    TenantClient         string    // Storacha tenant ID
    DataSources          []string  // URLs to fetch data
}
```

**Key files:** `filecoin-spade-client/pkg/spadeclient/spadeclient.go`

## P1 Details: Sector Size & Aggregation Constraints

Storacha uses **64 GiB sectors** (`StackedDrg64GiBV1_1`):
```go
proofType := abi.RegisteredSealProof_StackedDrg64GiBV1_1
```

**Aggregation thresholds (Go/Piri):**
```go
const MinAggregateSize = 128 << 20  // 128 MB minimum padded aggregate
```

- Single piece < 128 MB: remains buffered
- Single piece >= 128 MB: triggers immediate aggregate
- Two pieces together > 128 MB: triggers aggregate, buffer cleared

**JS aggregation config:**
```typescript
interface AggregateConfig {
  maxAggregateSize: number      // Hard limit on aggregate size
  minAggregateSize: number      // Minimum before aggregation
  minUtilizationFactor: number  // Fill factor requirement
  maxAggregatePieces?: number   // Hard limit on piece count
}
```

**Key files:** `piri/pkg/pdp/aggregation/aggregator/jobqueue.go`, `w3up/packages/filecoin-api/src/aggregator/api.ts`

## P1 Details: Deal Lifecycle States

**Aggregate states:**
```
offered → accepted → [on-chain tracking]
       └→ invalid (validation failure)
```

**SPADE deal states:**
```
pending → staged → active → terminated
```

**Deal record (JS):**
```typescript
interface DealRecord {
  piece: PieceLink       // Aggregate piece CID
  provider: string       // Storage provider f-address
  dealId: number         // Filecoin deal ID
  expirationEpoch: number
  source: string         // Where we learned about the deal
}
```

**Key files:** `w3up/packages/filecoin-api/src/deal-tracker/api.ts`, `spade/cron/trackdeals.go`

## Design Rationale

- **Two pipeline paths**: JS pipeline goes through Spade for traditional Filecoin deals (cold storage). Go pipeline (Piri/PDP) uses Ethereum for hot storage proofs. Both compute CommP but diverge after.
- **Receipt chain for traceability**: The fork/join effect system lets `filecoin/accept` trace back through the entire pipeline to return the complete proof, without blocking the initial request.
- **Queued async processing**: CommP computation and aggregation are expensive — they're enqueued as async jobs rather than computed in-request.
- **assert/equals bridges systems**: The equals claim linking content CID to piece CID is what connects the content addressing world (CIDs, DAGs) to the Filecoin world (CommP, deals).
- **128 MB minimum aggregate**: Ensures reasonable utilization within 64 GiB sectors while not waiting too long to submit deals.

## Authoritative Specs
- [W3 Filecoin Spec](https://github.com/storacha/specs/blob/main/w3-filecoin.md)
- [Filecoin Piece CID (data-segment)](https://github.com/filecoin-project/FIPs/blob/master/FRCs/frc-0058.md)
- [PDP (Proof of Data Possession)](https://github.com/storacha/specs/blob/main/pdp.md)
