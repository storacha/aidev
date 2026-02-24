<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Filecoin Deal Flow: End-to-End Trace

> **TL;DR:** Two pipelines. JS: `filecoin/offer` -> `filecoin/submit` -> `piece/offer` -> `piece/accept` -> `aggregate/offer` -> `aggregate/accept` -> `deal/info`, using fork/join effects and queues at each step. Go (Piri/PDP): `blob/accept` triggers async CommP calculation, aggregation into proof sets, and Ethereum smart contract submission for Provable Data Possession challenges. `filecoin/accept` traces the receipt chain back to return complete proof (piece, aggregate, inclusion proof, deal info).

## Two Pipelines

```
JS Pipeline (w3up/filecoin-api)              Go Pipeline (Piri/PDP)

filecoin/offer (agent, per shard)            blob/accept
    │                                             │
    ├→ filecoin/submit (storefront)              ├→ CommP calculation (async queue)
    │     └→ piece/offer (aggregator)            ├→ assert/location claim
    │           └→ piece/accept                  └→ pdp/accept (async)
    │                 └→ aggregate/offer                │
    │                       └→ aggregate/accept         ├→ aggregation into proof set
    │                             └→ deal/info          └→ Ethereum smart contract
    │                                                        (challenge/prove)
    └→ filecoin/accept (traces receipt chain back)
```

## JS Pipeline: Step by Step

### Step 1: filecoin/offer (Agent → Storefront)

| | |
|---|---|
| **Client** | `w3up/packages/upload-client/src/index.js` (inline during upload per shard) |
| **Server** | `w3up/packages/filecoin-api/src/storefront/service.js` |
| **Capability** | `filecoin/offer` with `nb: { content: blobCID, piece: pieceCID }` |

**Client side:** CommP computed during upload: `pieceHasher.digest(bytes)` → piece CID (multicodec 0x1011)

**Server handler:**
1. Check if piece already in `pieceStore`
2. If not: queue `filecoinSubmitQueue.add({ piece, content, group })`
3. Create effects: `fork(filecoin/submit)`, `join(filecoin/accept)`
4. Return `{ piece }`

### Step 2: filecoin/submit (Storefront, async)

| | |
|---|---|
| **File** | `w3up/packages/filecoin-api/src/storefront/service.js` (filecoinSubmitProvider) |
| **Events** | `w3up/packages/filecoin-api/src/storefront/events.js` |
| **Capability** | `filecoin/submit` |

Queue consumer processes the submit:
1. Verify piece info (`pieceStore`)
2. Create `assert/equals` claim linking content CID to piece CID
3. Invoke `piece/offer` on the aggregator service

### Step 3: piece/offer (Aggregator)

| | |
|---|---|
| **File** | `w3up/packages/filecoin-api/src/aggregator/service.js` |
| **Capability** | `piece/offer` with `nb: { piece, group }` |

1. Check if piece already known (`pieceStore`)
2. Queue for aggregation (`pieceOfferQueue.add({ piece, group })`)
3. Create effects: `fork(piece/offer)`, `join(piece/accept)`

### Step 4: piece/accept (Aggregator, async)

| | |
|---|---|
| **File** | `w3up/packages/filecoin-api/src/aggregator/service.js` |
| **Events** | `w3up/packages/filecoin-api/src/aggregator/events.js` |
| **Capability** | `piece/accept` |

When enough pieces accumulate, the aggregator:
1. Builds an aggregate (tree of pieces)
2. Computes aggregate CommP
3. Computes inclusion proofs for each piece
4. Invokes `aggregate/offer` on the dealer

### Step 5: aggregate/offer (Dealer)

| | |
|---|---|
| **File** | `w3up/packages/filecoin-api/src/dealer/service.js` |
| **Capability** | `aggregate/offer` with `nb: { aggregate: aggregatePiece, pieces: piecesBlock }` |

1. Store aggregate info (`aggregateStore`)
2. Queue for deal-making
3. Create effects: `join(aggregate/accept)`

### Step 6: aggregate/accept (Dealer, async)

| | |
|---|---|
| **File** | `w3up/packages/filecoin-api/src/dealer/service.js` |
| **Capability** | `aggregate/accept` |

Resolves when a Filecoin deal is confirmed:
1. Query deal-tracker for deal status
2. Return `{ aggregate, dataType, pieces }` with deal info

### Step 7: filecoin/accept (Storefront, traces back)

| | |
|---|---|
| **File** | `w3up/packages/filecoin-api/src/storefront/service.js` |
| **Capability** | `filecoin/accept` |

Traces the full receipt chain backward:
1. Follow `filecoin/submit` receipt → `piece/offer` → `piece/accept` → `aggregate/offer` → `aggregate/accept`
2. Extract: piece, aggregate, inclusion proof, deal info
3. Return complete proof: `{ piece, aggregate, inclusionProof, dealInfo }`

## Go Pipeline (Piri/PDP): Step by Step

### Step 1: blob/accept triggers PDP

| | |
|---|---|
| **File** | `piri/pkg/service/storage/handlers/blob/accept.go` |

When blob/accept processes (after blob stored):
1. Enqueue CommP calculation: `s.PDP().CommpCalculate().Enqueue(ctx, req.Blob.Digest)`
2. Create `pdp/accept` invocation (resolves when aggregation completes)
3. Create `assert/location` claim
4. Return with effects: `fx.WithFork(locationClaim, pieceAccept)`

### Step 2: CommP Calculation (async)

| | |
|---|---|
| **File** | `piri/pkg/pdp/aggregation/commp/commp.go` |
| **Trigger** | Async job queue |

1. Fetch blob bytes
2. FR32 pad the data
3. Build binary Merkle tree (SHA2-256-trunc254)
4. Root = CommP (piece commitment)
5. Store piece record

### Step 3: Aggregation

| | |
|---|---|
| **File** | `piri/pkg/pdp/aggregation/aggregator/aggregate.go` |

1. Collect pieces (sorted largest to smallest)
2. Build aggregate CommP using stack-based Merkle tree
3. Compute inclusion proofs for each piece
4. Create proof set for Ethereum submission

### Step 4: Ethereum Smart Contract

| | |
|---|---|
| **File** | `piri/pkg/pdp/` |

1. Submit proof set to Ethereum smart contract
2. Challenge window opens — storage node must respond to challenges
3. Generate proofs on demand during challenge window
4. Proof set remains active for ongoing verification

## Claims Published

| Step | Claim | What it asserts |
|------|-------|-----------------|
| filecoin/submit | `assert/equals` | Content CID equals CommP piece CID |
| blob/accept (both) | `assert/location` | Blob is at specific URL |
| index/add (earlier) | `assert/index` | Content indexed by ShardedDAGIndex |

## Queue/Event Processing

| Queue | Consumer | Located in |
|-------|----------|-----------|
| filecoinSubmitQueue | Storefront event handler | `filecoin-api/src/storefront/events.js` |
| pieceOfferQueue | Aggregator event handler | `filecoin-api/src/aggregator/events.js` |
| aggregateOfferQueue | Dealer event handler | `filecoin-api/src/dealer/events.js` |
| CommpCalculate | PDP job worker | `piri/pkg/pdp/aggregation/commp/` |

## Key Files

| Role | File |
|------|------|
| Storefront service | `w3up/packages/filecoin-api/src/storefront/service.js` |
| Storefront events | `w3up/packages/filecoin-api/src/storefront/events.js` |
| Aggregator service | `w3up/packages/filecoin-api/src/aggregator/service.js` |
| Dealer service | `w3up/packages/filecoin-api/src/dealer/service.js` |
| Deal-tracker service | `w3up/packages/filecoin-api/src/deal-tracker/service.js` |
| Filecoin capabilities | `w3up/packages/capabilities/src/filecoin/` |
| PDP blob/accept (Go) | `piri/pkg/service/storage/handlers/blob/accept.go` |
| Go CommP calculator | `piri/pkg/pdp/aggregation/commp/commp.go` |
| Go aggregator | `piri/pkg/pdp/aggregation/aggregator/aggregate.go` |
