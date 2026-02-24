<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Upload Flow: End-to-End Trace

> **TL;DR:** File upload is a 7-step pipeline: (1) UnixFS encode into blocks, (2) shard into ~127MB CARs, (3) `blob/add` per shard (allocate presigned URL -> HTTP PUT to R2 -> accept + location claim), (4) `filecoin/offer` per shard, (5) store ShardedDAGIndex as blob, (6) `index/add` (publish to IPNI + index claim), (7) `upload/add` (register root -> shards mapping). Client entry: `w3up/packages/upload-client/src/index.js`.

## Overview

```
File/Directory
    │
    ├── 1. UnixFS encode → block stream
    ├── 2. ShardingStream → CAR shards (~127MB each)
    │
    │   For each shard:
    ├── 3. blob/add → orchestrates allocation, HTTP PUT, acceptance
    │     ├── 3a. web3.storage/blob/allocate → presigned URL
    │     ├── 3b. http/put → client uploads bytes to R2
    │     └── 3c. web3.storage/blob/accept → confirms storage, publishes location claim
    ├── 4. filecoin/offer → enters Filecoin pipeline (per shard)
    │
    ├── 5. blob/add (index) → store the ShardedDAGIndex as a blob
    ├── 6. index/add → register index, publish to IPNI + content claims
    └── 7. upload/add → register upload (root CID → shard CIDs)
```

## Step-by-Step Trace

### Step 1: Client Entry Point

| | |
|---|---|
| **Repo** | w3up (upload-client) |
| **File** | `w3up/packages/upload-client/src/index.js` |
| **Functions** | `uploadFile()`, `uploadDirectory()`, `uploadCAR()` → all call `uploadBlockStream()` |
| **Required capabilities** | `blob/add`, `index/add`, `filecoin/offer`, `upload/add` |

```
uploadFile(conf, file) → UnixFS.createFileEncoderStream(file) → uploadBlockStream()
uploadDirectory(conf, files) → UnixFS.createDirectoryEncoderStream(files) → uploadBlockStream()
uploadCAR(conf, car) → CAR.BlockStream(car) → uploadBlockStream()
```

### Step 2: Encode + Shard

| | |
|---|---|
| **File** | `w3up/packages/upload-client/src/unixfs.js`, `src/sharding.js` |
| **Class** | `ShardingStream` (TransformStream) |
| **Config** | Shard size: 133,169,152 bytes (~127MB), UnixFS: 1MB chunks, width 1024, raw leaves |

```js
blocks
  .pipeThrough(new ShardingStream(options))  // → IndexedCARFile per shard
  .pipeThrough(transformStream)               // → blob/add + filecoin/offer per shard
  .pipeTo(writableStream)                     // → collect metadata
```

Each shard is an `IndexedCARFile` with: `{ version, roots, size, slices: Map<digest, [offset, length]> }`

### Step 3: blob/add (per shard)

| | |
|---|---|
| **Client** | `w3up/packages/upload-client/src/blob/index.js` → `Blob.add(conf, digest, bytes)` |
| **Server handler** | `w3up/packages/upload-api/src/blob/add.js` → `blobAddProvider()` |
| **Capability** | `blob/add` with `nb: { blob: { digest, size } }` |
| **Pattern** | `Server.provideAdvanced` with fork/join effects |

The `blob/add` handler orchestrates 3 sub-steps:

#### Step 3a: web3.storage/blob/allocate

| | |
|---|---|
| **File** | `w3up/packages/upload-api/src/blob/allocate.js` |
| **Capability** | `web3.storage/blob/allocate` (self-issued by service) |
| **Infra** | `provisionsStorage` (DynamoDB), `allocationsStorage` (DynamoDB), `blobsStorage` (R2/S3) |

1. Check space has storage provider (`provisionsStorage.hasStorageProvider`)
2. Check blob size within limits (`maxUploadSize`)
3. Insert allocation record (`allocationsStorage.insert`)
4. Check if blob already exists (`blobsStorage.has`)
5. If not exists: create presigned upload URL (`blobsStorage.createUploadUrl`, 24h expiry)
6. Return `{ size, address: { url, headers, expiresAt } }`

#### Step 3b: http/put (client uploads bytes)

| | |
|---|---|
| **File** | `w3up/packages/upload-api/src/blob/add.js` (put function) |
| **Capability** | `http/put` with `nb: { body: blob, url: ucan/await, headers: ucan/await }` |
| **Infra** | R2/S3 via presigned URL |

- URL and headers come from `ucan/await` referencing the allocate receipt
- Client performs HTTP PUT to the presigned URL with blob bytes
- If blob already stored (no address returned), receipt issued immediately
- Issuer: `blobProvider` derived from `ed25519.derive(blob.digest)` — any actor with the blob can sign

#### Step 3c: web3.storage/blob/accept

| | |
|---|---|
| **File** | `w3up/packages/upload-api/src/blob/accept.js` |
| **Capability** | `web3.storage/blob/accept` (self-issued by service) |
| **Infra** | `blobsStorage` (R2), `claimsService` (content-claims) |

1. Verify blob exists in storage (`blobsStorage.has`)
2. Create download URL (`blobsStorage.createDownloadUrl`)
3. Create `assert/location` delegation (content → download URL)
4. Publish location claim to content-claims service (`Assert.location.invoke()`)
5. Return `{ site: locationClaim.cid }` + fork location claim

**Trigger for accept:** When an `http/put` receipt arrives via `ucan/conclude`, the `poll()` function in `blob/accept.js` detects it, looks up the corresponding `blob/allocate`, and executes `blob/accept`.

### Step 4: filecoin/offer (per shard)

| | |
|---|---|
| **Client** | `w3up/packages/upload-client/src/index.js` (inline in transform) |
| **Function** | `Storefront.filecoinOffer()` from `@web3-storage/filecoin-client` |
| **Capability** | `filecoin/offer` with `nb: { content: blobCID, piece: pieceCID }` |

- CommP (piece CID) computed client-side: `pieceHasher.digest(bytes)` using FR32 hasher
- Piece CID: `Link.create(raw.code, multihashDigest)` with multicodec 0x1011
- Enters the Filecoin pipeline (see `filecoin-deal-flow.md`)

### Step 5: Store the index blob

| | |
|---|---|
| **Client** | `w3up/packages/upload-client/src/index.js` (after all shards) |
| **Function** | `indexShardedDAG(root, shards, shardIndexes)` → `Blob.add(conf, indexDigest, indexBytes)` |

The ShardedDAGIndex maps every block in the DAG to its byte range within a shard:
```js
const indexBytes = await indexShardedDAG(root, shards, shardIndexes)
const indexDigest = await sha256.digest(indexBytes.ok)
const indexLink = Link.create(CAR.code, indexDigest)
await Blob.add(blobAddConf, indexDigest, indexBytes.ok)  // same blob/add flow as shards
```

### Step 6: index/add

| | |
|---|---|
| **Client** | `w3up/packages/upload-client/src/index/index.js` → `Index.add()` |
| **Server handler** | `w3up/packages/upload-api/src/index/add.js` |
| **Capability** | `index/add` with `nb: { index: indexLink }` |
| **Infra** | `allocationsStorage`, `blobRetriever`, `ipniService`, `claimsService` |

1. Verify index blob is allocated in space (`assertAllocated`)
2. Fetch index blob from storage (`blobRetriever.stream`)
3. Parse as ShardedDAGIndex (`ShardedDAGIndex.extract`)
4. Verify all referenced shards are allocated
5. **Publish to IPNI** (`ipniService.publish(index)`) — makes blocks discoverable
6. **Publish index claim** (`Assert.index.invoke()`) — links content to index

### Step 7: upload/add

| | |
|---|---|
| **Client** | `w3up/packages/upload-client/src/upload/index.js` → `Upload.add()` |
| **Server handler** | `w3up/packages/upload-api/src/upload/add.js` |
| **Capability** | `upload/add` with `nb: { root: rootCID, shards: [shardCID...] }` |
| **Infra** | `uploadTable` (DynamoDB) |

1. Allocate space (`space-allocate.js`)
2. Upsert upload record: `{ space, root, shards, issuer, invocation }`
3. Returns the upload record

## Infrastructure Summary

| Step | Infrastructure | Purpose |
|------|---------------|---------|
| Allocation | DynamoDB (`allocationsStorage`) | Track blob → space mappings |
| Provisioning check | DynamoDB (`provisionsStorage`) | Verify space has storage provider |
| Blob storage | R2/S3 (`blobsStorage`) | Store raw blob bytes |
| HTTP PUT | Presigned URL to R2 | Client direct upload |
| Location claim | Content Claims service | Record where blob is stored |
| IPNI publish | IPNI service | Make blocks discoverable by multihash |
| Index claim | Content Claims service | Link content root to index |
| Upload record | DynamoDB (`uploadTable`) | Track root CID → shard CIDs |

## Claims Published

| Claim | When | What it asserts |
|-------|------|-----------------|
| `assert/location` | blob/accept | Blob is at download URL with byte range |
| `assert/index` | index/add | Content DAG is indexed by ShardedDAGIndex |
| `assert/equals` | filecoin/submit (later) | Blob CID equals CommP piece CID |
