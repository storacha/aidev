<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Content Claims & Indexing: Patterns & Reference

> **TL;DR:** Content discovery has two parallel paths: IPNI (multihash -> provider records) and Content Claims (signed UCAN assertions chained as equals -> location -> index). The Indexing Service (Go) unifies both, resolving CIDs to retrievable blob URLs + byte ranges. Primary claims: `assert/location` (from `blob/accept`) and `assert/index` (from `index/add`). ShardedDAGIndex is the pivot structure mapping blocks to byte positions within CAR shards. Custom IPNI metadata protocols: 0x3E0000-0x3E0002.

> Concepts: Content Claims protocol (P0), Sharded DAG Index (P0), IPNI publishing (P0), claim types (P0), indexing service (P0)
> Key repos: content-claims, w3up (blob-index, upload-api), indexing-service, ipni-publisher

## How Content Discovery Works

```
Upload time:                          Query time:

  blob/add → store CAR shards         GET /ipfs/<CID>
  index/add → extract ShardedDAGIndex    |
     |                                   v
     ├→ publish to IPNI               Indexing Service
     │   (multihash → provider)          |
     └→ publish index claim              ├→ IPNI lookup (multihash → provider)
         (assert/index)                  ├→ content-claims lookup
                                         │   (follow equals→location→index chain)
  blob/accept → location claim           └→ resolve to blob URL + byte range
     (assert/location)                       |
                                             v
                                         blob-fetcher → HTTP range request → R2
```

**Two parallel discovery paths:**
1. **IPNI**: Multihash → provider records (who has it, how to get it)
2. **Content Claims**: Claim chain walking (equals→location→index→byte range)

The indexing service unifies both: it queries IPNI for provider records, then follows content claim chains to resolve content to retrievable locations.

## Claim Types

| Claim | Capability | What It Asserts | When Created |
|-------|-----------|-----------------|--------------|
| **Location** | `assert/location` | CID is at URL(s) with byte range | `blob/accept` receipt |
| **Index** | `assert/index` | Content DAG is indexed by a ShardedDAGIndex | `index/add` handler |
| **Inclusion** | `assert/inclusion` | CAR contains blocks described by an index | Legacy uploads |
| **Partition** | `assert/partition` | Content spans multiple CAR parts | Legacy uploads |
| **Relation** | `assert/relation` | CID links to child CIDs, with part info | Legacy uploads |
| **Equals** | `assert/equals` | Two CIDs refer to same data | Cross-system mapping (e.g., CID↔CommP) |

**Primary claims in the current system:** `assert/location` and `assert/index`. Others are from the legacy content-claims system.

## Patterns

### Pattern: Publish a location claim (Go — blob/accept handler)
**When:** After blob storage is confirmed, record where content lives
**Template:**
```go
import "github.com/storacha/go-libstoracha/capabilities/assert"

byteRange := assert.Range{Offset: 0, Length: &req.Blob.Size}
claim, err := assert.Location.Delegate(
    signer,              // service signer
    req.Space,           // audience: space DID
    signer.DID().String(), // resource: service DID
    assert.LocationCaveats{
        Space:    req.Space,
        Content:  types.FromHash(req.Blob.Digest),
        Location: []url.URL{downloadURL},
        Range:    &byteRange,
    },
    delegation.WithNoExpiration(),
)
// Store and publish the claim
claimsStore.Put(ctx, claim)
claimsPublisher.Publish(ctx, claim)
```
**Key files:** `piri/pkg/service/storage/handlers/blob/accept.go:127-143`

### Pattern: Create and publish a Sharded DAG Index
**When:** After all shards are uploaded, create the index that maps blocks to byte ranges
**Template:**
```js
import { ShardedDAGIndex } from '@web3-storage/blob-index/sharded-dag-index'

// Create index from upload pipeline output
const index = ShardedDAGIndex.create(rootCID)
for (const [shardDigest, slices] of shardIndexes) {
  for (const [blockMultihash, [offset, length]] of slices) {
    index.setSlice(shardDigest, blockMultihash, [offset, length])
  }
}
const { ok: archiveBytes } = await index.archive()  // → CAR file bytes

// Store as blob, then register
await Blob.add(conf, await sha256.digest(archiveBytes), archiveBytes)
await Index.add(conf, Link.create(0x0202, indexDigest))
```
**Key files:** `w3up/packages/blob-index/src/sharded-dag-index.js`, `w3up/packages/upload-client/src/index.js`
**Gotchas:**
- Index is itself stored as a blob (CAR file) with its own CID
- `index.archive()` produces a CAR with dag-cbor encoded blocks:
  - Root: `{ "index/sharded/dag@0.1": { content, shards: [CID...] } }`
  - Per-shard blocks: `[shardMultihashBytes, [[blockMultihash, [offset, length]], ...]]`
- Lookups use multihash (not full CID) — codec-agnostic

### Pattern: Handle index/add (server side)
**When:** Service receives an index registration
**Template:**
```js
const add = async ({ capability }, context) => {
  const space = capability.with
  const idxLink = capability.nb.index

  // 1. Verify index blob is allocated in space
  await assertAllocated(context, space, idxLink.multihash, 'IndexNotFound')

  // 2. Fetch and parse the index
  const idxBlobRes = await context.blobRetriever.stream(idxLink.multihash)
  const idxRes = ShardedDAGIndex.extract(concat(chunks))

  // 3. Verify all referenced shards are allocated
  for (const shardDigest of idxRes.ok.shards.keys()) {
    await assertAllocated(context, space, shardDigest, 'ShardNotFound')
  }

  // 4. Publish to IPNI + create index claim
  await Promise.all([
    context.ipniService.publish(idxRes.ok),
    publishIndexClaim(context, { content: idxRes.ok.content, index: idxLink }),
  ])
  return ok({})
}
```
**Key files:** `w3up/packages/upload-api/src/index/add.js`

### Pattern: Query the indexing service (Go)
**When:** Resolving a CID to retrievable locations
**Template:**
```go
// The indexing service walks claim chains:
// 1. Lookup multihash in IPNI → provider records
// 2. For each provider: fetch claims by contextID
// 3. Follow equals→location→index chain
// 4. Return resolved locations with byte ranges

result, err := indexingService.Query(ctx, types.Query{
    Hashes: []multihash.Multihash{targetMultihash},
})
// result contains: index claims, location claims per shard
```
**Key files:** `indexing-service/pkg/service/service.go`

### Pattern: Read claims from content-claims service (JS client)
**When:** Looking up claims for a piece of content
**Template:**
```js
import * as Claims from '@web3-storage/content-claims/client'

// Fetch claims by multihash (HTTP GET, returns CAR stream)
const claims = await Claims.read(content.multihash, {
  serviceURL: 'https://claims.web3.storage',
  walk: ['parts', 'includes'],  // follow related claims
})
// claims is an array of decoded UCAN invocations
```
**Key files:** `content-claims/packages/core/src/client/index.js`
**Gotchas:**
- HTTP API: `GET /claims/multihash/<base58btc>` returns a CAR stream
- `?walk=parts,includes` parameter follows related claims transitively
- Each claim is a signed UCAN invocation — verified on read

### Pattern: Publish IPNI advertisements (Go)
**When:** Making content discoverable via IPNI
**Template:**
```go
import "github.com/storacha/ipni-publisher/pkg/publisher"

pub := publisher.NewIPNIPublisher(...)
link, err := pub.Publish(ctx, providerInfo, contextID, digestIterator, metadata)
// Creates a signed advertisement in the IPNI chain
// contextID groups related multihashes for updates/removal
```
**Key files:** `ipni-publisher/pkg/publisher/publisher.go`
**Gotchas:**
- Advertisements form a signed linked list (each links to previous)
- ContextID groups multihashes — used for updates and removal (IsRm=true)
- Announcements notify indexers of new advertisements (HTTP or gossipsub)

## Sharded DAG Index Structure

```
ShardedDAGIndex (CAR file, dag-cbor encoded)
├── Root block: { "index/sharded/dag@0.1": {
│     content: <content root CID>,
│     shards: [<shard1 CID>, <shard2 CID>, ...]
│   }}
├── Shard1 block: [
│     <shard1 multihash bytes>,
│     [
│       [<block1 multihash>, [offset1, length1]],
│       [<block2 multihash>, [offset2, length2]],
│       ...
│     ]
│   ]
└── Shard2 block: [...]
```

## Key Files Index

| Role | File |
|------|------|
| Claim capability defs (JS) | `content-claims/packages/core/src/capability/assert.js` |
| Claim capability defs (Go) | `go-libstoracha/capabilities/assert/` |
| Claim service handlers | `content-claims/packages/core/src/server/service/assert.js` |
| Claim client (HTTP) | `content-claims/packages/core/src/client/index.js` |
| ShardedDAGIndex impl | `w3up/packages/blob-index/src/sharded-dag-index.js` |
| index/add handler | `w3up/packages/upload-api/src/index/add.js` |
| IPNI publisher (Go) | `ipni-publisher/pkg/publisher/publisher.go` |
| Indexing service (Go) | `indexing-service/pkg/service/service.go` |
| Location claim (Go) | `piri/pkg/service/storage/handlers/blob/accept.go` |

## Key Types

```ts
// ShardedDAGIndex
type ShardedDAGIndex = {
  content: Link              // content root CID
  shards: Map<MultihashDigest, Map<MultihashDigest, [offset: number, length: number]>>
}

// Claim caveats
type LocationCaveats = { content: Link|Digest, location: URI[], range?: {offset, length?}, space?: DID }
type IndexCaveats = { content: Link|Digest, index: Link }
type InclusionCaveats = { content: Link|Digest, includes: Link, proof?: Link }
type EqualsCaveats = { content: Link|Digest, equals: Link }
type PartitionCaveats = { content: Link|Digest, blocks?: Link, parts: Link[] }
type RelationCaveats = { content: Link|Digest, children: Link[], parts: [{content, includes?}] }
```

## IPNI Quick Reference

- **Advertisement chain**: Signed linked list of content announcements
- **Lookup API**: `GET /ipni/v1/ad/cid/{cid}` or `/multihash/{mh}` → provider records
- **Provider record**: `{ Provider: {ID, Addrs}, ContextID, Metadata }`
- **Metadata**: Varint protocol ID + protocol-specific bytes (e.g., HTTP transport)
- **Announcements**: HTTP POST or libp2p gossipsub to notify indexers

## P1 Details: IPNI Internals

### EntryChunk Structure

Multihashes are stored in linked chunks of up to 16,384 entries:
```go
type EntryChunk struct {
    Entries []multihash.Multihash  // Up to MaxEntryChunkSize (16,384) entries
    Next    ipld.Link              // Link to next chunk (nil if final)
}
```

**Storage flow** (`go-libstoracha/ipnipublisher/store/store.go`):
- `PutEntries()` batches multihashes into chunks of up to 16,384
- Each chunk is stored and its CID becomes the `Next` link for the previous chunk
- Return value is the root CID (most recent chunk)

### Advertisement Chain Linking

Each advertisement links to the previous via `PreviousID`:
```go
// advertisementpublisher.go
prevHead, _ := p.store.Head(ctx)

for _, adv := range pendingAds {
    adv.PreviousID = prevLink    // Chain link
    adv.Sign(p.key)              // Sign with provider key
    lnk, _ := p.store.PutAdvert(ctx, adv)
    prevLink = lnk               // Next ad links here
}

// Update head to latest
head, _ := head.NewSignedHead(lnk.(cidlink.Link).Cid, p.topic, p.key)
p.store.ReplaceHead(ctx, prevHead, head)
```

IPNI indexers traverse the chain backwards from the head.

**Key files:** `go-libstoracha/ipnipublisher/publisher/advertisementpublisher.go`

### Storacha-Specific IPNI Metadata

Three custom protocol IDs (registered in multicodec table):

| Protocol ID | Name | Fields |
|-------------|------|--------|
| `0x3E0000` | IndexClaim | `{ Index: CID, Expiration: int64, Claim: CID }` |
| `0x3E0001` | EqualsClaim | `{ Equals: CID, Expiration: int64, Claim: CID }` |
| `0x3E0002` | LocationCommitment | `{ Shard?: CID, Range?: {Offset, Length}, Expiration: int64, Claim: CID }` |

All implement `HasClaim` interface to expose the claim CID. Serialized as CBOR (~100 bytes).

**Key files:** `go-libstoracha/metadata/metadata.go`

### IPNI Publish Flow (End-to-End)

```
assert/index invocation
  → indexing-service UCANService handler
    → service.Publish()
      → publishIndexClaim()
        1. Cache claim locally
        2. Fetch blob index, extract all multihashes
        3. Create IndexClaimMetadata
        4. Call provIndex.Publish(providerInfo, contextID, multihashes, metadata)
          → IPNIPublisher.publishAdvForIndex()
            → GenerateAd()
              1. store.PutEntries() → EntryChunk chain
              2. Build schema.Advertisement{
                   Provider, Addresses, Entries: chunkLink,
                   ContextID, Metadata: mdBytes, IsRm: false
                 }
            → AdvertisementPublisher.Commit()
              1. Link to previous head
              2. Sign advertisement
              3. Store in IPLD store
              4. Update head reference
              5. Announce via HTTP to indexers
```

### Content Routing Query Flow

```
GET /claims?multihash[]=X&spaces[]=DID
  → indexing-service GetClaimsHandler
    → service.Query()
      1. providerIndex.Find(multihash)
         a. Check local cache
         b. If miss: query IPNI (1500ms timeout)
         c. Cache results
         d. Filter by space DIDs
      2. For each provider result:
         a. Extract claim CID from metadata
         b. Fetch claim from provider: GET /claim/{cid}
         c. Follow claim chains (equals→location→index)
      3. Encode results as CAR file response
```

### ipni-publisher Package Structure

```
go-libstoracha/ipnipublisher/
├── publisher/
│   ├── publisher.go               # Main API: Publish(ctx, provider, contextID, digests, meta)
│   ├── advertisementpublisher.go  # Chains, signs, stores advertisements
│   ├── generate_ad.go             # Creates advertisements from entries + metadata
│   └── options.go
├── store/
│   ├── store.go                   # PublisherStore: AdvertStore + EntriesStore + HeadStore + ChunkLinkStore + MetadataStore
│   └── options.go
├── queue/
│   ├── queue.go                   # Advertisement queue interface
│   └── aws/                       # SQS implementation
├── notifier/
│   └── headstate.go               # State persistence
└── server/
    └── server.go                  # HTTP server for announcements
```

## Design Rationale

- **Content Claims are UCAN delegations**: Claims are signed invocations with the `assert/*` capability — they can be verified, delegated, and revoked using the same UCAN machinery as everything else
- **Two discovery systems (IPNI + Claims)**: IPNI provides fast global lookup by multihash; content claims provide richer semantic relationships (equals, relation). The indexing service bridges both.
- **ShardedDAGIndex as the pivot**: This single data structure solves "which shard has my block?" — it's the bridge between the content DAG (logical) and blob storage (physical)
- **Location claims from blob/accept**: The storage service creates location claims automatically when accepting blobs — no separate claim publication step needed for the common case
- **Custom metadata protocols**: Storacha registers its own IPNI metadata types (0x3E0000-0x3E0002) to encode claim type and CID efficiently (~100 bytes), enabling clients to fetch full claims on demand
- **ContextID for grouping**: Each advertisement groups related multihashes under a contextID, enabling efficient updates and removal (IsRm=true advertisements)

## Authoritative Specs
- [W3 Index Spec](https://github.com/storacha/specs/blob/main/w3-index.md)
- [IPNI Specs](https://github.com/ipni/specs)
- [Content Claims Source](https://github.com/storacha/content-claims)
- [Indexing Service Source](https://github.com/storacha/indexing-service)
