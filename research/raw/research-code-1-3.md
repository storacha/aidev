# Research: Code Discovery for Topics 1-3

Research date: 2026-02-19
Codebase: 82 repos under 

---

## Topic 1: Content Addressing (CID, Multihash, Multicodec, IPLD Blocks, Blockstores)

### 1.1 How CIDs Are Created in JavaScript

**Canonical pattern: hash bytes, then CID.createV1(codec, multihash)**

File: `w3up/packages/upload-client/test/helpers/block.js`
```js
import { CID } from 'multiformats/cid'
import * as raw from 'multiformats/codecs/raw'
import { sha256 } from 'multiformats/hashes/sha2'

/** @param {Uint8Array} bytes */
export async function toBlock(bytes) {
  const hash = await sha256.digest(bytes)
  const cid = CID.createV1(raw.code, hash)
  return { cid, bytes }
}
```

**Alternative: CID.create(version, codec, hash)**

File: `w3up/packages/w3up-client/test/helpers/car.js`
```js
import { CID } from 'multiformats/cid'
import * as raw from 'multiformats/codecs/raw'
import { sha256 } from 'multiformats/hashes/sha2'

const hash = await sha256.digest(bytes)
const root = CID.create(1, raw.code, hash)
```

**Creating CIDs from links (after hashing CAR bytes):**

File: `w3up/packages/upload-client/src/index.js` (line 165)
```js
import * as Link from 'multiformats/link'
import * as raw from 'multiformats/codecs/raw'
import { sha256 } from 'multiformats/hashes/sha2'
import * as CAR from './car.js'

const digest = await sha256.digest(bytes)
const cid = Link.create(CAR.code, digest)  // CAR.code = 0x0202
// ...
const piece = Link.create(raw.code, multihashDigest)
```

**Test utility: deterministic CIDs using identity hash**

File: `freeway/test/unit/middleware/util/createTestCID.js`
```js
import { CID } from 'multiformats'
import * as raw from 'multiformats/codecs/raw'
import { identity } from 'multiformats/hashes/identity'

export const createTestCID = (n) => {
  return CID.createV1(raw.code, identity.digest(Uint8Array.of(n)))
}
```

**CID.parse for string-to-CID conversion:**

File: `w3up/packages/upload-client/test/sharding.test.js` (line 38)
```js
const rootCID = CID.parse(
  'bafybeibrqc2se2p3k4kfdwg7deigdggamlumemkiggrnqw3edrjosqhvnm'
)
```

**CID.decode for bytes-to-CID (rare, used in w3name):**

File: `w3name/packages/client/src/index.ts`

### 1.2 How CIDs Are Created in Go

**Canonical pattern: cid.NewCidV1(codec, multihash)**

File: `go-pail/clock/event/event.go` (line 160-165)
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

**Alternative: cid.Prefix for random/test CIDs**

File: `go-pail/internal/testutil/gen.go`
```go
import (
    "github.com/ipfs/go-cid"
    cidlink "github.com/ipld/go-ipld-prime/linking/cid"
    mh "github.com/multiformats/go-multihash"
)

func RandomLink(t *testing.T) datamodel.Link {
    bytes := RandomBytes(t, 10)
    c, _ := cid.Prefix{
        Version:  1,
        Codec:    cid.Raw,
        MhType:   mh.SHA2_256,
        MhLength: -1,
    }.Sum(bytes)
    return cidlink.Link{Cid: c}
}
```

### 1.3 Multicodec Codes Used

From file: `w3up/packages/capabilities/src/filecoin/lib.js`
```js
const RAW_CODE = /** @type {const} */ (0x55)
```

Key codes found across the codebase:
- `raw.code` (0x55) -- used everywhere for raw block data, file chunks, piece CIDs
- `dagCBOR.code` (0x71) -- used for dag-cbor encoded structures (sharded-dag-index, go-pail events/shards)
- `0x0202` -- CAR codec code (from `@ucanto/transport/car`), used in `store.js` and `car.js`
- `json.code` -- used in blob-fetcher test helpers for JSON-encoded CIDs

File: `w3up/packages/upload-client/src/car.js` (line 9)
```js
export const code = 0x0202
```

File: `w3up/packages/capabilities/src/store.js` (line 15-17)
```js
// @see https://github.com/multiformats/multicodec/blob/master/table.csv#L140
export const code = 0x0202
export const CARLink = Schema.link({ code, version: 1 })
```

### 1.4 Import Patterns for multiformats

The standard imports seen across the codebase:

```js
import { CID } from 'multiformats/cid'          // or 'multiformats'
import * as raw from 'multiformats/codecs/raw'
import { sha256 } from 'multiformats/hashes/sha2'
import { identity } from 'multiformats/hashes/identity'
import * as Link from 'multiformats/link'
import * as Digest from 'multiformats/hashes/digest'
import * as dagCBOR from '@ipld/dag-cbor'
import { base58btc } from 'multiformats/bases/base58'
import { base64 } from 'multiformats/bases/base64'
```

### 1.5 Blockstore Patterns

**Go: MapBlockstore (in-memory)**

File: `go-pail/block/mapblockstore.go`
```go
type MapBlockstore struct {
    data  map[ipld.Link]Block
    mutex sync.RWMutex
}

func (bs *MapBlockstore) Get(ctx context.Context, link ipld.Link) (Block, error) {
    bs.mutex.RLock()
    defer bs.mutex.RUnlock()
    b, ok := bs.data[link]
    if !ok { return nil, ErrNotFound }
    return b, nil
}

func (bs *MapBlockstore) Put(ctx context.Context, b Block) error {
    bs.mutex.Lock()
    bs.data[b.Link()] = b
    bs.mutex.Unlock()
    return nil
}
```

**JS: Hoverboard/Freeway blockstore (production gateway)**

File: `hoverboard/src/blocks.js`

Defines a layered blockstore architecture:
- `BlockStore` -- wraps a `BatchingFetcher` and `Locator` from `@web3-storage/blob-fetcher`
- `CachingBlockStore` -- wraps BlockStore with Cache API for byte caching
- `CachingLocator` -- wraps Locator with Cache API for index caching
- `DenyingBlockStore` -- wraps with deny list filtering

```js
export class BlockStore {
  constructor (locator, metrics) {
    this.fetcher = BatchingFetcher.create(locator)
    this.locator = locator
  }

  async has (cid) {
    const res = await this.locator.locate(cid.multihash)
    return Boolean(res.ok)
  }

  async get (cid) {
    const res = await this.fetcher.fetch(cid.multihash)
    if (res.ok) {
      const bytes = await res.ok.bytes()
      return bytes
    }
  }
}
```

**JS blockstore interface** (from hoverboard):
```js
/** @typedef {object} Blockstore
 *  @prop {(cid: UnknownLink) => Promise<boolean>} has
 *  @prop {(cid: UnknownLink) => Promise<Uint8Array | undefined>} get
 */
```

---

## Topic 2: CAR & UnixFS

### 2.1 CAR File Creation

**Canonical: CarWriter.create(root) from @ipld/car**

File: `w3up/packages/upload-client/src/car.js`
```js
import { CarBlockIterator, CarWriter } from '@ipld/car'

export async function encode(blocks, root) {
  const { writer, out } = CarWriter.create(root)
  void (async () => {
    try {
      for await (const block of blocks) {
        await writer.put(block)
      }
    } finally {
      await writer.close()
    }
  })()
  const chunks = []
  for await (const chunk of out) chunks.push(chunk)
  const roots = root != null ? [root] : []
  return Object.assign(new Blob(chunks), { version: 1, roots })
}
```

**Gateway CAR streaming (CarWriter for HTTP responses):**

File: `gateway-lib/src/handlers/car.js`
```js
import { CarWriter } from '@ipld/car'

const { writer, out } = CarWriter.create(dataCid)
;(async () => {
  try {
    for await (const block of dag.getPath(`${dataCid}${path}`, { dagScope })) {
      await writer.put(block)
    }
  } finally {
    await writer.close()
  }
})()
return new Response(toReadableStream(out), { headers })
```

**Test helper: creating a one-block CAR**

File: `w3up/packages/w3up-client/test/helpers/car.js`
```js
import { CarWriter } from '@ipld/car'
import { CID } from 'multiformats/cid'
import * as raw from 'multiformats/codecs/raw'
import { sha256 } from 'multiformats/hashes/sha2'
import * as CAR from '@ucanto/transport/car'

export async function toCAR(bytes) {
  const hash = await sha256.digest(bytes)
  const root = CID.create(1, raw.code, hash)
  const { writer, out } = CarWriter.create(root)
  writer.put({ cid: root, bytes })
  writer.close()
  const chunks = []
  for await (const chunk of out) chunks.push(chunk)
  const blob = new Blob(chunks)
  const cid = await CAR.codec.link(new Uint8Array(await blob.arrayBuffer()))
  return Object.assign(blob, { cid, roots: [root], bytes })
}
```

### 2.2 CAR File Parsing

**CarBlockIterator for streaming block extraction:**

File: `w3up/packages/upload-client/src/car.js` (BlockStream class)
```js
import { CarBlockIterator } from '@ipld/car'

export class BlockStream extends ReadableStream {
  constructor(car) {
    let blocksPromise = null
    const getBlocksIterable = () => {
      if (blocksPromise) return blocksPromise
      blocksPromise = CarBlockIterator.fromIterable(toIterable(car.stream()))
      return blocksPromise
    }
    let iterator = null
    super({
      async start() {
        const blocks = await getBlocksIterable()
        iterator = blocks[Symbol.asyncIterator]()
      },
      async pull(controller) {
        const { value, done } = await iterator.next()
        if (done) return controller.close()
        controller.enqueue(value)
      },
    })
    this.getRoots = async () => {
      const blocks = await getBlocksIterable()
      return await blocks.getRoots()
    }
  }
}
```

**CAR decoding in blob-index (via ucanto CAR codec):**

File: `w3up/packages/blob-index/src/sharded-dag-index.js` (line 38-52)
```js
import { CAR } from '@ucanto/core'
import * as dagCBOR from '@ipld/dag-cbor'

export const extract = (archive) => {
  const { roots, blocks } = CAR.decode(archive)
  if (!roots.length) {
    return error(new UnknownFormat('missing root block'))
  }
  const { code } = roots[0].cid
  if (code !== dagCBOR.code) {
    return error(new UnknownFormat(`unexpected root CID codec: 0x${code.toString(16)}`))
  }
  return view({ root: roots[0], blocks })
}
```

### 2.3 UnixFS Creation

**Core implementation: encodeFile and createFileEncoderStream**

File: `w3up/packages/upload-client/src/unixfs.js`
```js
import * as UnixFS from '@ipld/unixfs'
import * as raw from 'multiformats/codecs/raw'
import { withMaxChunkSize } from '@ipld/unixfs/file/chunker/fixed'
import { withWidth } from '@ipld/unixfs/file/layout/balanced'

const defaultSettings = UnixFS.configure({
  fileChunkEncoder: raw,
  smallFileEncoder: raw,
  chunker: withMaxChunkSize(1024 * 1024),  // 1MB chunks
  fileLayout: withWidth(1024),
})

export function createFileEncoderStream(blob, options) {
  const { readable, writable } = new TransformStream({}, queuingStrategy)
  const settings = options?.settings ?? defaultSettings
  const unixfsWriter = UnixFS.createWriter({ writable, settings })
  const fileBuilder = new UnixFSFileBuilder('', blob)
  void (async () => {
    await fileBuilder.finalize(unixfsWriter)
    await unixfsWriter.close()
  })()
  return readable
}
```

**Directory encoding (with sharding for large dirs > 1000 items):**

File: `w3up/packages/upload-client/src/unixfs.js` (line 72-102)
```js
const SHARD_THRESHOLD = 1000

class UnixFSDirectoryBuilder {
  async finalize(writer) {
    const dirWriter =
      this.entries.size <= SHARD_THRESHOLD
        ? UnixFS.createDirectoryWriter(writer)
        : UnixFS.createShardedDirectoryWriter(writer)
    for (const [name, entry] of this.entries) {
      const link = await entry.finalize(writer)
      dirWriter.set(name, link)
    }
    return await dirWriter.close()
  }
}
```

### 2.4 Sharding Logic (How Large Files Split Into Multiple CARs)

**ShardingStream -- the core sharding TransformStream**

File: `w3up/packages/upload-client/src/sharding.js`
```js
const SHARD_SIZE = 133_169_152  // ~127MB default

export class ShardingStream extends TransformStream {
  constructor(options = {}) {
    const shardSize = options.shardSize ?? SHARD_SIZE
    const maxBlockLength = shardSize - headerEncodingLength()
    let blocks = []
    let currentLength = 0

    super({
      async transform(block, controller) {
        if (readyBlocks != null && readySlices != null) {
          controller.enqueue(await encodeCAR(readyBlocks, readySlices))
          readyBlocks = null; readySlices = null
        }
        const blockLength = blockHeaderEncodingLength(block) + block.bytes.length
        if (blocks.length && currentLength + blockLength > maxBlockLength) {
          readyBlocks = blocks; readySlices = slices
          blocks = []; slices = new DigestMap(); currentLength = 0
        }
        blocks.push(block)
        slices.set(block.cid.multihash, [
          headerEncodingLength() + currentLength + blockHeaderEncodingLength(block),
          block.bytes.length,
        ])
        currentLength += blockLength
      },
      async flush(controller) {
        // ... handles the final shard with rootCID, overflow logic
      },
    })
  }
}
```

**Full upload pipeline: file -> UnixFS blocks -> shards -> blob/add -> index/add -> upload/add**

File: `w3up/packages/upload-client/src/index.js` (lines 135-257)
```js
async function uploadBlockStream(conf, blocks, options) {
  const shardIndexes = []
  const shards = []
  let root = null

  await blocks
    .pipeThrough(new ShardingStream(options))       // blocks -> CAR shards
    .pipeThrough(new TransformStream({
      async transform(car, controller) {
        const bytes = new Uint8Array(await car.arrayBuffer())
        const digest = await sha256.digest(bytes)
        await Blob.add(conf, digest, bytes, options)  // store each shard
        const cid = Link.create(CAR.code, digest)
        // ... filecoin offer
        controller.enqueue({ cid, slices: car.slices, ... })
      },
    }))
    .pipeTo(new WritableStream({
      write(meta) {
        root = root || meta.roots[0]
        shards.push(meta.cid)
        shardIndexes.push(meta.slices)
      },
    }))

  // Create sharded DAG index
  const indexBytes = await indexShardedDAG(root, shards, shardIndexes)
  const indexDigest = await sha256.digest(indexBytes.ok)
  const indexLink = Link.create(CAR.code, indexDigest)

  await Blob.add(blobAddConf, indexDigest, indexBytes.ok, options)
  await Index.add(indexAddConf, indexLink, options)
  await Upload.add(uploadAddConf, root, shards, options)

  return root
}
```

### 2.5 Sharded DAG Index Format

File: `w3up/packages/blob-index/src/sharded-dag-index.js`

The index is a CAR file containing dag-cbor blocks:
- Root block: `{ "index/sharded/dag@0.1": { content: <DAG root CID>, shards: [<shard CIDs>] } }`
- Shard blocks: `[<shard multihash bytes>, [[<slice multihash>, [offset, length]], ...]]`

```js
export const version = 'index/sharded/dag@0.1'

export const archive = async (model) => {
  const blocks = new Map()
  const index = { content: model.content, shards: [] }
  for (const s of shards) {
    const slices = [...s[1].entries()].map((e) => [e[0].bytes, e[1]])
    const bytes = dagCBOR.encode([s[0].bytes, slices])
    const digest = await sha256.digest(bytes)
    const cid = Link.create(dagCBOR.code, digest)
    blocks.set(cid.toString(), { cid, bytes })
    index.shards.push(cid)
  }
  const bytes = dagCBOR.encode({ [version]: index })
  const digest = await sha256.digest(bytes)
  const cid = Link.create(dagCBOR.code, digest)
  return ok(CAR.encode({ roots: [{ cid, bytes }], blocks }))
}
```

### 2.6 CAR-Related Test File

File: `w3up/packages/upload-client/test/sharding.test.js`
```js
it('creates shards from blocks', async () => {
  const file = new Blob([await randomBytes(1024 * 1024 * 5)])
  const shardSize = 1024 * 1024 * 2
  const shards = []

  await createFileEncoderStream(file)
    .pipeThrough(new ShardingStream({ shardSize }))
    .pipeTo(new WritableStream({
      write: (s) => { shards.push(s) },
    }))

  assert(shards.length > 1)
  for (const car of shards) {
    assert(car.size <= shardSize + 100)
  }
})
```

---

## Topic 3: ucanto Framework

### 3.1 Capability Definitions

The pattern is: `capability({ can, with, nb, derives })` from `@ucanto/validator`.

**Example 1: Space blob/add (with Schema.struct nb)**

File: `w3up/packages/capabilities/src/blob.js` (line 58-72)
```js
import { capability, Schema, fail, ok } from '@ucanto/validator'
import { SpaceDID } from './utils.js'

export const add = capability({
  can: 'space/blob/add',
  with: SpaceDID,
  nb: Schema.struct({
    blob: Schema.struct({
      digest: Schema.bytes(),
      size: Schema.integer(),
    }),
  }),
  derives: equalBlob,
})
```

**Example 2: Upload/add (with Link caveats)**

File: `w3up/packages/capabilities/src/upload.js` (line 54-78)
```js
import { capability, Link, Schema, ok } from '@ucanto/validator'
import { codec as CAR } from '@ucanto/transport/car'

const CARLink = Link.match({ code: CAR.code, version: 1 })

export const add = capability({
  can: 'upload/add',
  with: SpaceDID,
  nb: Schema.struct({
    root: Link,
    shards: CARLink.array().optional(),
  }),
  derives: (self, from) => {
    return (
      and(equalWith(self, from)) ||
      and(equal(self.nb.root, from.nb.root, 'root')) ||
      and(equal(self.nb.shards, from.nb.shards, 'shards')) ||
      ok({})
    )
  },
})
```

**Example 3: Store/add (with size constraint in derives)**

File: `w3up/packages/capabilities/src/store.js` (line 41-83)
```js
export const add = capability({
  can: 'store/add',
  with: SpaceDID,
  nb: Schema.struct({
    link: CARLink,
    size: Schema.integer(),
    origin: Link.optional(),
  }),
  derives: (claim, from) => {
    const result = equalLink(claim, from)
    if (result.error) return result
    else if (claim.nb.size !== undefined && from.nb.size !== undefined) {
      return claim.nb.size > from.nb.size
        ? fail(`Size constraint violation: ${claim.nb.size} > ${from.nb.size}`)
        : ok({})
    }
    return ok({})
  },
})
```

**Example 4: Access/authorize (with DID method constraint)**

File: `w3up/packages/capabilities/src/access.js` (line 65-80)
```js
export const authorize = capability({
  can: 'access/authorize',
  with: DID.match({ method: 'key' }),
  nb: Schema.struct({
    iss: Account.optional(),
    att: CapabilityRequest.array(),
  }),
  derives: (child, parent) => {
    return (
      and(equalWith(child, parent)) ||
      and(equal(child.nb.iss, parent.nb.iss, 'iss')) ||
      and(subsetCapabilities(child.nb.att, parent.nb.att)) ||
      ok({})
    )
  },
})
```

**Example 5: Content claims assert/location**

File: `content-claims/packages/core/src/capability/assert.js`
```js
export const location = capability({
  can: 'assert/location',
  with: URI.match({ protocol: 'did:' }),
  nb: Schema.struct({
    content: linkOrDigest(),
    location: Schema.array(URI),
    range: Schema.struct({
      offset: Schema.integer(),
      length: Schema.integer().optional()
    }).optional(),
    space: Schema.principal().optional()
  }),
  derives: (claimed, delegated) => (
    and(equalWith(claimed, delegated)) ||
    and(equalLinkOrDigestContent(claimed, delegated)) ||
    and(equal(claimed.nb.location, delegated.nb.location, 'location')) ||
    ok({})
  )
})
```

**Example 6: Filecoin/offer**

File: `w3up/packages/capabilities/src/filecoin/storefront.js` (line 32-56)
```js
export const filecoinOffer = capability({
  can: 'filecoin/offer',
  with: Schema.did(),
  nb: Schema.struct({
    content: Schema.link(),
    piece: PieceLink,
  }),
  derives: (claim, from) => {
    return (
      and(equalWith(claim, from)) ||
      and(checkLink(claim.nb.content, from.nb.content, 'nb.content')) ||
      and(checkLink(claim.nb.piece, from.nb.piece, 'nb.piece')) ||
      ok({})
    )
  },
})
```

**Example 7: PDP/accept (upload-service monorepo -- newer)**

File: `upload-service/packages/capabilities/src/pdp.js`
```js
export const accept = capability({
  can: 'pdp/accept',
  with: Schema.did(),
  nb: Schema.struct({
    blob: Schema.bytes(),
  }),
  derives: (claim, from) => {
    return (
      and(equalWith(claim, from)) ||
      and(equal(claim.nb.blob, from.nb.blob, 'blob')) ||
      ok({})
    )
  },
})
```

**Example 8: Claim/cache (upload-service)**

File: `upload-service/packages/capabilities/src/claim.js`
```js
export const cache = capability({
  can: 'claim/cache',
  with: URI.match({ protocol: 'did:' }),
  nb: Schema.struct({
    claim: Schema.link({ version: 1 }),
    provider: Schema.struct({
      addresses: Schema.array(Schema.bytes()),
    }),
  }),
  derives: (claimed, delegated) =>
    and(equalWith(claimed, delegated)) ||
    and(equal(claimed.nb.claim, delegated.nb.claim, 'claim')) ||
    and(equalProviderAddresses(claimed, delegated)) ||
    ok({}),
})
```

### 3.2 Server.provide / provideAdvanced Patterns

**Pattern A: Simple provide (most handlers)**

File: `w3up/packages/upload-api/src/upload/add.js`
```js
import * as Server from '@ucanto/server'
import * as Upload from '@web3-storage/capabilities/upload'

export function uploadAddProvider(context) {
  return Server.provide(Upload.add, async ({ capability, invocation }) => {
    const { root, shards } = capability.nb
    const space = Server.DID.parse(capability.with).did()
    return uploadTable.upsert({ space, root, shards, issuer: invocation.issuer.did() })
  })
}
```

**Pattern B: provideAdvanced (for effect/fork workflows)**

File: `w3up/packages/upload-api/src/blob/add.js`
```js
export function blobAddProvider(context) {
  return Server.provideAdvanced({
    capability: Blob.add,
    handler: async ({ capability, invocation }) => {
      const { with: space, nb } = capability
      const allocation = await allocate({ context, blob: nb.blob, space, cause: invocation.link() })
      const delivery = await put({ blob: nb.blob, allocation })
      const acceptance = await accept({ context, blob: nb.blob, space, delivery })

      let result = Server.ok({
        site: { 'ucan/await': ['.out.ok.site', acceptance.task.link()] },
      })
        .fork(allocation.task)
        .fork(delivery.task)
        .fork(acceptance.task)

      for (const task of [...allocation.fx, ...delivery.fx, ...acceptance.fx]) {
        result = result.fork(task)
      }
      return result
    },
  })
}
```

**Pattern C: provideAdvanced with audience schema**

File: `freeway/src/server/service.js`
```js
export function createService(ctx, env) {
  return {
    access: {
      delegate: UcantoServer.provideAdvanced({
        capability: AccessCapabilities.delegate,
        audience: Schema.did({ method: 'web' }).or(Schema.did({ method: 'key' })),
        handler: async ({ capability, invocation, context }) => {
          // ... handler logic
          return ok({})
        }
      })
    }
  }
}
```

**Pattern D: Simple provide with error returns**

File: `w3up/packages/upload-api/src/blob/allocate.js` (line 14-15)
```js
export const blobAllocateProvider = (context) =>
  Server.provide(W3sBlob.allocate, (input) => allocate(context, input))
```

**Pattern E: index/add -- provide with content claim publishing**

File: `w3up/packages/upload-api/src/index/add.js`
```js
export const provide = (context) =>
  Server.provide(Index.add, (input) => add(input, context))

const add = async ({ capability }, context) => {
  const space = capability.with
  const idxLink = capability.nb.index
  // Fetch, validate, publish index claim
  const idxBlobRes = await context.blobRetriever.stream(idxLink.multihash)
  const idxRes = ShardedDAGIndex.extract(concat(chunks))
  await context.ipniService.publish(idxRes.ok)
  await publishIndexClaim(context, { content: idxRes.ok.content, index: idxLink })
  return ok({})
}
```

### 3.3 Service Factory / Wiring Pattern

**Top-level service composition:**

File: `w3up/packages/upload-api/src/lib.js` (line 176-194)
```js
export const createService = (context) => ({
  access: createAccessService(context),
  console: createConsoleService(context),
  consumer: createConsumerService(context),
  customer: createCustomerService(context),
  provider: createProviderService(context),
  'rate-limit': createRateLimitService(context),
  admin: createAdminService(context),
  space: createSpaceService(context),
  store: createStoreService(context),
  subscription: createSubscriptionService(context),
  upload: createUploadService(context),
  ucan: createUcanService(context),
  plan: createPlanService(context),
  ['web3.storage']: createW3sService(context),
  filecoin: createFilecoinService(context).filecoin,
  usage: createUsageService(context),
})
```

**Sub-service factory (blob as example):**

File: `w3up/packages/upload-api/src/blob.js`
```js
export function createService(context) {
  return {
    add: blobAddProvider(context),
    list: blobListProvider(context),
    remove: blobRemoveProvider(context),
    get: { 0: { 1: blobGetProvider(context) } },  // versioned: blob/get/0/1
  }
}
```

**w3.storage sub-service:**

File: `w3up/packages/upload-api/src/service.js`
```js
export function createService(context) {
  return {
    blob: {
      allocate: blobAllocateProvider(context),
      accept: blobAcceptProvider(context),
    },
  }
}
```

### 3.4 Server Creation

File: `w3up/packages/upload-api/src/lib.js` (line 34-60)
```js
import * as Server from '@ucanto/server/server'
import * as Legacy from '@ucanto/transport/legacy'
import * as CAR from '@ucanto/transport/car'

export const createServer = ({ codec = Legacy.inbound, ...options }) => {
  const context = { ...options, ...createRevocationChecker(options) }

  const server = Server.create({
    ...context,
    codec,
    service: createService(context),
    catch: (error) => context.errorReporter.catch(error),
  })
  // ... wraps with agent message handling, receipt caching
  return agent
}
```

**Simpler server creation (w3clock):**

File: `w3clock/src/server/index.js`
```js
import * as Server from '@ucanto/server'
import * as CAR from '@ucanto/transport/car'

export function createServer(signer, service) {
  return Server.create({
    id: signer,
    codec: CAR.inbound,
    service,
    catch: err => console.error(err),
    validateAuthorization: () => ({ ok: {} }),
  })
}
```

**Canonical test setup:**

File: `ucanto/packages/server/test/server.spec.js` (line 71-82)
```js
const server = Server.create({
  service: Service.create(),
  codec: CAR.inbound,
  id: w3,
  validateAuthorization: () => ({ ok: {} }),
})

const connection = Client.connect({
  id: w3,
  codec: CAR.outbound,
  channel: server,
})
```

### 3.5 Connection Setup

**Production connection (w3infra config):**

File: `w3infra/upload-api/config.js` (line 46-60)
```js
import { CAR, HTTP } from '@ucanto/transport'
import { connect } from '@ucanto/client'

export function getServiceConnection(config) {
  const servicePrincipal = DID.parse(config.did) // 'did:web:up.storacha.network'
  const serviceURL = new URL(config.url)
  const serviceConnection = connect({
    id: servicePrincipal,
    codec: CAR.outbound,
    channel: HTTP.open({ url: serviceURL, method: 'POST' }),
  })
  return serviceConnection
}
```

**Client library connection (w3clock):**

File: `w3clock/src/client/index.js` (line 93-100)
```js
import { connect as clientConnect } from '@ucanto/client'
import { CAR, HTTP } from '@ucanto/transport'
import * as DID from '@ipld/dag-ucan/did'

export function connect(options) {
  const url = options?.serviceURL ?? new URL(SERVICE_URL)
  return clientConnect({
    id: options?.servicePrincipal ?? DID.parse(SERVICE_PRINCIPAL),
    codec: CAR.outbound,
    channel: HTTP.open({ url, method: 'POST' })
  })
}
```

**Inline connection in lib.js:**

File: `w3up/packages/upload-api/src/lib.js` (line 202-207)
```js
export const connect = ({ id, channel, codec = CAR.outbound }) =>
  Client.connect({ id, channel, codec })
```

**CLI connection setup:**

File: `w3cli/lib.js` (line 8-10)
```js
import { connect } from '@ucanto/client'
import * as CAR from '@ucanto/transport/car'
import * as HTTP from '@ucanto/transport/http'
```

### 3.6 Effect System (ok/error/fork/join builders)

File: `ucanto/packages/server/src/handler.js` (line 101-267)

The effect system is used when handlers need to produce side effects (forked tasks):

```js
// Server.ok(value) returns an OkBuilder
export const ok = value => new Ok(value)

// OkBuilder has .fork(task) and .join(task) methods
class Ok {
  constructor(ok) { this.ok = ok }
  get result() { return { ok: this.ok } }
  get effects() { return { fork: [] } }
  fork(run) { return new Fork({ out: this.result, fx: { fork: [run] } }) }
  join(run) { return new Join({ out: this.result, fx: { fork: [], join: run } }) }
}

// Fork allows chaining additional forks
class Fork extends Join {
  fork(run) {
    const { out, fx } = this.do
    return new Fork({ out, fx: { ...fx, fork: [...fx.fork, run] } })
  }
  join(run) {
    const { out, fx } = this.do
    return new Join({ out, fx: { ...fx, join: run } })
  }
}
```

**Real usage of effects in blob/add:**

File: `w3up/packages/upload-api/src/blob/add.js` (line 59-76)
```js
let result = Server.ok({
  site: { 'ucan/await': ['.out.ok.site', acceptance.task.link()] },
})
  .fork(allocation.task)    // fork: run allocation task
  .fork(delivery.task)      // fork: run HTTP PUT task
  .fork(acceptance.task)    // fork: run blob/accept task

// Add conclude invocations as additional forked effects
for (const task of [...allocation.fx, ...delivery.fx, ...acceptance.fx]) {
  result = result.fork(task)
}
return result
```

**Effect in blob/accept:**

File: `w3up/packages/upload-api/src/blob/accept.js` (line 70-74)
```js
const result = Server.ok({ site: locationClaim.cid })
return result.fork(locationClaim)  // fork the location claim delegation
```

### 3.7 Transport Layer

The transport pattern is always:
- Inbound: `CAR.inbound` (server-side codec for decoding requests)
- Outbound: `CAR.outbound` (client-side codec for encoding requests)
- Channel: `HTTP.open({ url, method: 'POST' })` (HTTP transport)

File: `w3infra/upload-api/config.js`
```js
import { CAR, HTTP } from '@ucanto/transport'

// Server side:
Server.create({ codec: CAR.inbound, ... })

// Client side:
connect({ codec: CAR.outbound, channel: HTTP.open({ url, method: 'POST' }) })
```

### 3.8 Schema Patterns

Schema types used in capability definitions:
- `Schema.struct({...})` -- object with named fields
- `Schema.bytes()` -- Uint8Array
- `Schema.integer()` -- integer number
- `Schema.string()` -- string
- `Schema.boolean()` -- boolean
- `Schema.link()` -- any CID link
- `Schema.link({ version: 1 })` -- CIDv1 only
- `Schema.link({ code: 0x0202, version: 1 })` -- specific codec + version
- `Schema.did()` -- any DID
- `Schema.did({ method: 'key' })` -- did:key only
- `Schema.array(...)` -- array of schema
- `Schema.dictionary({ value: ... })` -- dictionary/map
- `Schema.principal()` -- DID principal
- `Schema.number()` -- number
- `Schema.tuple([...])` -- fixed-length tuple
- `.optional()` -- make field optional
- `.or(...)` -- union types
- `.greaterThan(n)` -- numeric constraint
- `Schema.variant({...})` -- tagged union
- `URI` / `URI.match({ protocol: 'did:' })` -- URI schema
- `DID` / `DID.match({ method: 'mailto' })` -- DID schema
- `Link` / `Link.match({ code, version })` -- CID link schema

### 3.9 Capability Invocation Pattern (Client Side)

File: `w3clock/src/client/index.js` (line 20-35)
```js
const invocation = ClockCaps.advance
  .invoke({
    issuer,
    audience: audience ?? conn.id,
    with: resource,
    nb: { event },
    proofs,
    facts
  })

for (const block of options?.blocks ?? []) {
  invocation.attach(block)
}

return invocation.execute(conn)
```

### 3.10 Capability Catalog Summary

From the API surface map and code discovery, here are the known capabilities organized by domain:

**Core Storage:**
- `space/blob/*`, `space/blob/add`, `space/blob/remove`, `space/blob/list`, `space/blob/get/0/1`
- `store/*`, `store/add`, `store/remove`, `store/list`, `store/get`
- `upload/*`, `upload/add`, `upload/remove`, `upload/list`, `upload/get`

**Service-Internal (web3.storage namespace):**
- `web3.storage/blob/allocate`, `web3.storage/blob/accept`
- `http/put`

**Indexing:**
- `index/add`

**Content Claims (assert namespace):**
- `assert/*`, `assert/location`, `assert/inclusion`, `assert/index`
- `assert/partition`, `assert/relation`, `assert/equals`

**Access Control:**
- `access/*`, `access/authorize`, `access/confirm`, `access/claim`, `access/delegate`

**Space Management:**
- `space/*`, `space/info`, `space/allocate`
- `space/content/serve/*`, `space/content/serve/transport/http`
- `space/content/serve/egress/record`

**Account/Billing:**
- `plan/get`, `plan/set`, `plan/create-admin-session`, `plan/create-checkout-session`
- `customer/*`, `consumer/*`, `subscription/*`
- `usage/*`, `usage/report`

**Filecoin Pipeline:**
- `filecoin/*`, `filecoin/offer`, `filecoin/submit`, `filecoin/accept`, `filecoin/info`

**PDP (upload-service, newer):**
- `pdp/accept`, `pdp/info`

**Claims (upload-service, newer):**
- `claim/*`, `claim/cache`

**Admin:**
- `admin/*`

**UCAN meta:**
- `ucan/attest`, `ucan/revoke`, `ucan/conclude`
- `*` (top capability)

---

## Key Files Index

### Topic 1 Files
| Purpose | Path |
|---------|------|
| CID creation (JS canonical) | `repos/storacha/w3up/packages/upload-client/test/helpers/block.js` |
| CID creation (Go canonical) | `repos/storacha/go-pail/clock/event/event.go` |
| CID creation (Go test util) | `repos/storacha/go-pail/internal/testutil/gen.go` |
| Test CID factory | `repos/storacha/freeway/test/unit/middleware/util/createTestCID.js` |
| Blockstore (Go) | `repos/storacha/go-pail/block/mapblockstore.go` |
| Blockstore (JS gateway) | `repos/storacha/hoverboard/src/blocks.js` |
| CAR codec code (0x0202) | `repos/storacha/w3up/packages/upload-client/src/car.js` |
| Store capability (CARLink) | `repos/storacha/w3up/packages/capabilities/src/store.js` |
| Filecoin lib (RAW_CODE) | `repos/storacha/w3up/packages/capabilities/src/filecoin/lib.js` |

### Topic 2 Files
| Purpose | Path |
|---------|------|
| CAR encode/decode | `repos/storacha/w3up/packages/upload-client/src/car.js` |
| UnixFS encoding | `repos/storacha/w3up/packages/upload-client/src/unixfs.js` |
| Sharding stream | `repos/storacha/w3up/packages/upload-client/src/sharding.js` |
| Upload pipeline | `repos/storacha/w3up/packages/upload-client/src/index.js` |
| Sharded DAG index | `repos/storacha/w3up/packages/blob-index/src/sharded-dag-index.js` |
| Sharding tests | `repos/storacha/w3up/packages/upload-client/test/sharding.test.js` |
| CAR in gateway | `repos/storacha/gateway-lib/src/handlers/car.js` |
| Test CAR helper | `repos/storacha/w3up/packages/w3up-client/test/helpers/car.js` |

### Topic 3 Files
| Purpose | Path |
|---------|------|
| provide/provideAdvanced impl | `repos/storacha/ucanto/packages/server/src/handler.js` |
| Effect system (ok/error/fork) | `repos/storacha/ucanto/packages/server/src/handler.js` |
| Blob capabilities | `repos/storacha/w3up/packages/capabilities/src/blob.js` |
| Upload capabilities | `repos/storacha/w3up/packages/capabilities/src/upload.js` |
| Store capabilities | `repos/storacha/w3up/packages/capabilities/src/store.js` |
| Access capabilities | `repos/storacha/w3up/packages/capabilities/src/access.js` |
| Space capabilities | `repos/storacha/w3up/packages/capabilities/src/space.js` |
| Filecoin capabilities | `repos/storacha/w3up/packages/capabilities/src/filecoin/storefront.js` |
| Content claims caps | `repos/storacha/content-claims/packages/core/src/capability/assert.js` |
| PDP capabilities (new) | `repos/storacha/upload-service/packages/capabilities/src/pdp.js` |
| Claim capabilities (new) | `repos/storacha/upload-service/packages/capabilities/src/claim.js` |
| Assert capabilities (new) | `repos/storacha/upload-service/packages/capabilities/src/assert.js` |
| Serve capability | `repos/storacha/freeway/src/capabilities/serve.js` |
| Service composition | `repos/storacha/w3up/packages/upload-api/src/lib.js` |
| Blob service factory | `repos/storacha/w3up/packages/upload-api/src/blob.js` |
| Upload service factory | `repos/storacha/w3up/packages/upload-api/src/upload.js` |
| W3s service factory | `repos/storacha/w3up/packages/upload-api/src/service.js` |
| blob/add handler | `repos/storacha/w3up/packages/upload-api/src/blob/add.js` |
| blob/allocate handler | `repos/storacha/w3up/packages/upload-api/src/blob/allocate.js` |
| blob/accept handler | `repos/storacha/w3up/packages/upload-api/src/blob/accept.js` |
| upload/add handler | `repos/storacha/w3up/packages/upload-api/src/upload/add.js` |
| index/add handler | `repos/storacha/w3up/packages/upload-api/src/index/add.js` |
| Connection (production) | `repos/storacha/w3infra/upload-api/config.js` |
| Connection (client lib) | `repos/storacha/w3clock/src/client/index.js` |
| Server creation (w3clock) | `repos/storacha/w3clock/src/server/index.js` |
| Server test | `repos/storacha/ucanto/packages/server/test/server.spec.js` |
| Handler test | `repos/storacha/ucanto/packages/server/test/handler.spec.js` |
| Freeway service | `repos/storacha/freeway/src/server/service.js` |
| CLI imports | `repos/storacha/w3cli/lib.js` |
| API surface map | `output/storacha/api-surface-map.json` |
