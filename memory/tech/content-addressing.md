<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Content Addressing: Patterns & Reference

> **TL;DR:** CIDs (Content Identifiers) are Storacha's universal addressing scheme -- hash the data with sha2-256, wrap in a multihash, encode as CIDv1. JS uses `multiformats` package, Go uses `go-cid`. Key rule: raw codec (0x55) for leaf blocks/blobs, dag-cbor (0x71) for structured IPLD data, 0x0202 for CAR files. Blockstore lookups always use `cid.multihash`, not the full CID.

> Concepts: CID (P0), Multihash (P0), Multicodec (P1), IPLD Data Model (P1), Blockstores (P1)
> Key repos: w3up, ucanto, freeway, go-pail, hoverboard, blob-fetcher, content-claims

## Patterns

### Pattern: Create a CID from bytes (JS)
**When:** You have raw data and need a content address
**Template:**
```js
import { CID } from 'multiformats/cid'
import * as raw from 'multiformats/codecs/raw'
import { sha256 } from 'multiformats/hashes/sha2'

const hash = await sha256.digest(bytes)
const cid = CID.createV1(raw.code, hash)
// Result: CIDv1 with raw codec (0x55) + sha2-256 hash
```
**Variations:**
- `CID.create(1, raw.code, hash)` — equivalent, explicit version
- `Link.create(codec, digest)` — from `multiformats/link`, used when you already have the multicodec code as a number (e.g. `Link.create(0x0202, digest)` for CAR CIDs)
- `CID.createV1(dagCBOR.code, hash)` — for structured IPLD data (dag-cbor 0x71)
- For tests: `CID.createV1(raw.code, identity.digest(Uint8Array.of(n)))` — deterministic test CIDs using identity hash
**Key files:** `w3up/packages/upload-client/test/helpers/block.js`, `freeway/test/unit/middleware/util/createTestCID.js`
**Gotchas:**
- Always use `sha256` from `multiformats/hashes/sha2`, not Web Crypto directly — multiformats wraps the digest with the correct varint prefix
- `raw.code` (0x55) is used for raw data/blobs; `dagCBOR.code` (0x71) for structured data — using the wrong codec means the CID won't decode correctly

### Pattern: Create a CID from bytes (Go)
**When:** Building CIDs in Go services
**Template:**
```go
import (
    "github.com/ipfs/go-cid"
    cidlink "github.com/ipld/go-ipld-prime/linking/cid"
    "github.com/multiformats/go-multihash"
    "github.com/multiformats/go-multicodec"
)

digest, err := multihash.Sum(bytes, multihash.SHA2_256, -1)
link := cidlink.Link{Cid: cid.NewCidV1(uint64(multicodec.DagCbor), digest)}
```
**Variations:**
- `cid.Prefix{Version: 1, Codec: cid.Raw, MhType: mh.SHA2_256, MhLength: -1}.Sum(bytes)` — for test utilities
- `cid.NewCidV1(cid.Raw, digest)` — for raw data
**Key files:** `go-pail/clock/event/event.go:160`, `go-pail/internal/testutil/gen.go`
**Gotchas:**
- Go uses `cidlink.Link` wrapper when working with go-ipld-prime — don't use raw `cid.Cid` with IPLD APIs
- `-1` for MhLength means "use default length for this hash"

### Pattern: Parse a CID from string
**When:** Converting user input or stored CID strings back to CID objects
**Template:**
```js
import { CID } from 'multiformats/cid'
const cid = CID.parse('bafybeibrqc2se2p3k4kfdwg7deigdggamlumemkiggrnqw3edrjosqhvnm')
```
**Gotchas:**
- `bafy...` prefix = CIDv1, base32lower encoding
- `Qm...` prefix = CIDv0, base58btc encoding (legacy IPFS)
- `CID.decode(bytes)` for binary CID (rare, used in w3name)

### Pattern: Blockstore interface (JS)
**When:** Implementing or consuming block storage
**Template:**
```js
// Minimal interface used throughout codebase:
/** @typedef {{ has(cid): Promise<boolean>, get(cid): Promise<Uint8Array|undefined> }} Blockstore */
```
**Variations:**
- Gateway production: `BlockStore` → `CachingBlockStore` → `DenyingBlockStore` layered architecture in `hoverboard/src/blocks.js`
- `BlockStore` wraps a `BatchingFetcher` + `Locator` from `@web3-storage/blob-fetcher`
- Lookup is by `cid.multihash` not full CID (codec-agnostic)
**Key files:** `hoverboard/src/blocks.js`, `blob-fetcher/src/fetcher/batching.js`

### Pattern: Blockstore interface (Go)
**When:** Go block storage
**Template:**
```go
type Blockstore interface {
    Get(ctx context.Context, link ipld.Link) (Block, error)
    Put(ctx context.Context, b Block) error
}
// In-memory: go-pail/block/MapBlockstore with sync.RWMutex
```
**Key files:** `go-pail/block/mapblockstore.go`

## Key Files Index

| Role | File |
|------|------|
| CID creation (JS canonical) | `w3up/packages/upload-client/test/helpers/block.js` |
| CID creation (Go canonical) | `go-pail/clock/event/event.go:160` |
| CID creation (Go test util) | `go-pail/internal/testutil/gen.go` |
| Test CID factory (JS) | `freeway/test/unit/middleware/util/createTestCID.js` |
| Blockstore (Go in-memory) | `go-pail/block/mapblockstore.go` |
| Blockstore (JS gateway prod) | `hoverboard/src/blocks.js` |
| CAR codec constant (0x0202) | `w3up/packages/upload-client/src/car.js:9` |
| CARLink schema | `w3up/packages/capabilities/src/store.js:15-17` |

## Key Types & Interfaces

```ts
// From multiformats
CID.createV1(codec: number, hash: MultihashDigest): CID
CID.create(version: 0|1, codec: number, hash: MultihashDigest): CID
CID.parse(str: string): CID
Link.create(codec: number, digest: MultihashDigest): Link

// MultihashDigest = { code: number, size: number, digest: Uint8Array, bytes: Uint8Array }
// CID fields: .version, .code (codec), .multihash, .bytes, .toString()
```

## Multicodec Quick Reference

| Code | Name | Usage in Storacha |
|------|------|-------------------|
| `0x55` | raw | File chunks, blob data, piece CIDs — dominant codec |
| `0x71` | dag-cbor | Structured IPLD data: sharded-dag-index, pail entries, UCAN tokens |
| `0x70` | dag-pb | UnixFS file trees (legacy, still used for directory structures) |
| `0x0129` | dag-json | Rare, debugging |
| `0x0202` | CAR | CAR file references (shard CIDs) |
| `0x12` | sha2-256 | Hash function code (in multihash, not CID codec) |

## Standard Imports

```js
import { CID } from 'multiformats/cid'          // or 'multiformats'
import * as raw from 'multiformats/codecs/raw'    // codec 0x55
import { sha256 } from 'multiformats/hashes/sha2' // hash 0x12
import { identity } from 'multiformats/hashes/identity' // test only
import * as Link from 'multiformats/link'
import * as Digest from 'multiformats/hashes/digest'
import * as dagCBOR from '@ipld/dag-cbor'         // codec 0x71
import { base58btc } from 'multiformats/bases/base58'
import { base64 } from 'multiformats/bases/base64'
```

## Spec Notes

**CID binary format (CIDv1):** `<multibase><version-varint><codec-varint><multihash>`
- String form: `<multibase-prefix><base-encoded-binary>` (base32lower 'b' prefix → `bafy...`)
- CIDv0: bare multihash, base58btc, always sha2-256 + dag-pb (legacy `Qm...`)

**Multihash format:** `<hash-function-varint><digest-length-varint><digest-bytes>`
- SHA2-256: code=0x12, length=32, total=34 bytes

**IPLD Data Model kinds:** Null, Bool, Int, Float, String, Bytes, List, Map, Link
- Link = CID reference to another block
- DAG-CBOR uses CBOR tag 42 (`0xd82a`) with `0x00` identity multibase prefix before binary CID

## Design Rationale

Content addressing ensures every piece of data has a unique, verifiable identifier derived from its content. This is foundational to Storacha because:
- **Deduplication**: Same content = same CID, regardless of who uploads it
- **Verification**: Receivers can verify content matches its CID without trusting the sender
- **Linking**: CIDs enable building verifiable DAG structures (Merkle DAGs) — the basis for UnixFS files, content claims, and the entire UCAN proof chain
- **Codec flexibility**: Different serializations (raw, dag-cbor, dag-pb) share the same addressing scheme

## Authoritative Specs
- [CID (Content Identifier) Spec](https://github.com/multiformats/cid)
- [Multihash](https://github.com/multiformats/multihash)
- [Multicodec Table](https://github.com/multiformats/multicodec/blob/master/table.csv)
- [IPLD Data Model](https://ipld.io/docs/data-model/)
- [IPLD Schemas](https://ipld.io/docs/schemas/)
