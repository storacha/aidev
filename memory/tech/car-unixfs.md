<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# CAR & UnixFS: Patterns & Reference

> **TL;DR:** Files are encoded as UnixFS block DAGs (1MB chunks, width-1024 balanced tree, raw leaves), then sharded into ~127MB CAR files for upload. Each shard gets its own CID (codec 0x0202). A ShardedDAGIndex maps every block to its byte offset within a shard, enabling partial retrieval. Key packages: `@ipld/car`, `@ipld/unixfs`, `@web3-storage/upload-client/sharding`.

> Concepts: CAR format (P1), UnixFS (P1), DAG-PB (P2), Sharding (P0), Sharded DAG Index (P0)
> Key repos: w3up (upload-client, blob-index), gateway-lib, freeway, hoverboard

## Patterns

### Pattern: Create a CAR file from blocks
**When:** Packaging content-addressed blocks for upload or transport
**Template:**
```js
import { CarWriter } from '@ipld/car'

const { writer, out } = CarWriter.create(rootCID)
// Writer runs async, out is an async iterable of chunks
void (async () => {
  try {
    for await (const block of blocks) {
      await writer.put(block) // block = { cid, bytes }
    }
  } finally {
    await writer.close()
  }
})()
const chunks = []
for await (const chunk of out) chunks.push(chunk)
const blob = new Blob(chunks)
```
**Variations:**
- Gateway streaming: pipe `out` directly to `new Response(toReadableStream(out), { headers })` — no buffering
- One-block test CAR: `writer.put({ cid: root, bytes }); writer.close()` then hash the blob to get the CAR CID: `Link.create(0x0202, await sha256.digest(carBytes))`
**Key files:** `w3up/packages/upload-client/src/car.js`, `gateway-lib/src/handlers/car.js`
**Gotchas:**
- `CarWriter.create(root)` takes an optional root CID — can also be `null` for rootless CARs
- Writer and output run concurrently (writer produces, out consumes) — must `await writer.close()` before reading is complete
- CAR CIDs use codec `0x0202` — this is the CID of the CAR file itself (hash of the whole CAR bytes), NOT the content root CID inside it

### Pattern: Parse/decode a CAR file
**When:** Reading blocks from a stored or received CAR
**Template (streaming):**
```js
import { CarBlockIterator } from '@ipld/car'

const blocks = await CarBlockIterator.fromIterable(carStream)
const roots = await blocks.getRoots()
for await (const { cid, bytes } of blocks) {
  // process each block
}
```
**Template (in-memory, ucanto style):**
```js
import { CAR } from '@ucanto/core'
const { roots, blocks } = CAR.decode(carBytes)
```
**Key files:** `w3up/packages/upload-client/src/car.js` (BlockStream class), `w3up/packages/blob-index/src/sharded-dag-index.js`

### Pattern: Encode a file as UnixFS blocks
**When:** Uploading a file — turning raw bytes into a content-addressed DAG
**Template:**
```js
import * as UnixFS from '@ipld/unixfs'
import * as raw from 'multiformats/codecs/raw'
import { withMaxChunkSize } from '@ipld/unixfs/file/chunker/fixed'
import { withWidth } from '@ipld/unixfs/file/layout/balanced'

const settings = UnixFS.configure({
  fileChunkEncoder: raw,       // raw codec (0x55) for leaf blocks
  smallFileEncoder: raw,       // raw codec for single-block files
  chunker: withMaxChunkSize(1024 * 1024),  // 1MB chunks
  fileLayout: withWidth(1024),              // balanced tree, width 1024
})

const { readable, writable } = new TransformStream()
const unixfsWriter = UnixFS.createWriter({ writable, settings })
// ... finalize file, then close writer
```
**Variations:**
- `createFileEncoderStream(blob, options)` — higher-level stream API from upload-client
- `UnixFS.createDirectoryWriter(writer)` — for directories
- `UnixFS.createShardedDirectoryWriter(writer)` — for directories with >1000 entries (HAMT sharding threshold)
**Key files:** `w3up/packages/upload-client/src/unixfs.js`
**Gotchas:**
- Default chunk size is **1MB** (not the spec default of 256KB) — Storacha uses larger chunks
- Default tree width is **1024** (not the spec default of 174) — wider trees, fewer levels
- Leaf blocks use `raw` codec (0x55), NOT the traditional `dag-pb` wrapping — produces canonical CIDs for single-block files
- Directories with >1000 entries automatically switch to HAMT-sharded format

### Pattern: Shard large uploads into multiple CARs
**When:** Uploading files that produce more blocks than fit in one CAR
**Template:**
```js
import { ShardingStream } from '@web3-storage/upload-client/sharding'

const SHARD_SIZE = 133_169_152  // ~127MB default

await createFileEncoderStream(file)
  .pipeThrough(new ShardingStream({ shardSize: SHARD_SIZE }))
  .pipeTo(new WritableStream({
    async write(car) {
      // car is a Blob with .roots, .slices properties
      // Store each shard: blob/add
    }
  }))
```
**Key files:** `w3up/packages/upload-client/src/sharding.js`
**Gotchas:**
- Default shard size is `133_169_152` bytes (~127MB), not a power of 2
- Each shard is a complete CAR file with its own header
- The root CID goes into the LAST shard (handles overflow)
- `car.slices` is a `DigestMap` tracking `[offset, length]` per block within that shard — used to build the Sharded DAG Index

### Pattern: Full upload pipeline
**When:** End-to-end file upload from client
**Template:**
```js
// file → UnixFS blocks → CAR shards → blob/add each → index/add → upload/add
await blocks
  .pipeThrough(new ShardingStream(options))      // blocks → CAR shards
  .pipeThrough(new TransformStream({
    async transform(car, controller) {
      const bytes = new Uint8Array(await car.arrayBuffer())
      const digest = await sha256.digest(bytes)
      await Blob.add(conf, digest, bytes)         // store shard via blob/add
      const cid = Link.create(0x0202, digest)     // CAR CID
      controller.enqueue({ cid, slices: car.slices, roots: car.roots })
    }
  }))
  .pipeTo(collector)

// After all shards stored:
const indexBytes = await indexShardedDAG(root, shardCIDs, shardIndexes)
await Blob.add(conf, indexDigest, indexBytes)     // store index as blob
await Index.add(conf, indexLink)                  // register index
await Upload.add(conf, root, shardCIDs)           // register upload
```
**Key files:** `w3up/packages/upload-client/src/index.js:135-257`

### Pattern: Sharded DAG Index (structure & creation)
**When:** Creating the index that maps DAG blocks to byte positions within CAR shards
**Template:**
```js
import { ShardedDAGIndex } from '@web3-storage/blob-index/sharded-dag-index'

// Version tag: 'index/sharded/dag@0.1'
// Structure (as dag-cbor CAR):
//   Root block: { "index/sharded/dag@0.1": { content: <root CID>, shards: [<shard CIDs>] } }
//   Shard blocks: [<shard multihash bytes>, [[<block multihash>, [offset, length]], ...]]

// To create:
const index = ShardedDAGIndex.create(rootCID)
for (const [shardDigest, sliceMap] of shardIndexes) {
  index.setSlice(shardDigest, blockMultihash, [offset, length])
}
const { ok: archiveBytes } = await index.archive()
```
**Variations:**
- `ShardedDAGIndex.extract(carBytes)` — parse an existing index from CAR bytes
**Key files:** `w3up/packages/blob-index/src/sharded-dag-index.js`
**Gotchas:**
- Index is itself a CAR file (root + blocks, all dag-cbor encoded)
- Maps content root CID → shard CIDs → per-block `[offset, length]` within each shard
- Offsets are byte offsets into the raw CAR file (including CAR header)
- Block lookup is by multihash, not full CID

## Key Files Index

| Role | File |
|------|------|
| CAR encode/decode | `w3up/packages/upload-client/src/car.js` |
| UnixFS encoding | `w3up/packages/upload-client/src/unixfs.js` |
| Sharding stream | `w3up/packages/upload-client/src/sharding.js` |
| Full upload pipeline | `w3up/packages/upload-client/src/index.js` |
| Sharded DAG Index | `w3up/packages/blob-index/src/sharded-dag-index.js` |
| CAR gateway handler | `gateway-lib/src/handlers/car.js` |
| Sharding tests | `w3up/packages/upload-client/test/sharding.test.js` |
| Test CAR helper | `w3up/packages/w3up-client/test/helpers/car.js` |

## Key Types & Interfaces

```ts
// CarWriter API
CarWriter.create(root?: CID): { writer: BlockWriter, out: AsyncIterable<Uint8Array> }
writer.put({ cid: CID, bytes: Uint8Array }): Promise<void>
writer.close(): Promise<void>

// CarBlockIterator
CarBlockIterator.fromIterable(source): AsyncIterable<{ cid: CID, bytes: Uint8Array }>

// ShardingStream
new ShardingStream({ shardSize?: number }): TransformStream<Block, CARBlob>
// CARBlob extends Blob with: .roots: CID[], .slices: DigestMap<[offset, length]>

// ShardedDAGIndex
ShardedDAGIndex.create(content: CID): ShardedDAGIndex
ShardedDAGIndex.extract(bytes: Uint8Array): Result<ShardedDAGIndex>
index.archive(): Promise<Result<Uint8Array>>
// Version tag: 'index/sharded/dag@0.1'
```

## Spec Notes

**CARv1 format:** `<dag-cbor-header><block>*`
- Header: dag-cbor `{version: 1, roots: [CID...]}` length-prefixed with varint
- Each block: `<varint-length><CID-bytes><data-bytes>`

**CARv2 format:** `<11-byte pragma><40-byte header>[padding]<CARv1 payload>[padding][index]`
- Pragma: `0x0a a16776657273696f6e02` (mimics CARv1 header with `version: 2`)
- Header: 128-bit characteristics bitfield + data offset/size/index offset (uint64 LE)
- Index formats: IndexSorted (0x0400), MultihashIndexSorted (0x0401)

**UnixFS Protobuf:** Type enum (Raw=0, Directory=1, File=2, Metadata=3, Symlink=4, HAMTShard=5)
- **Storacha defaults differ from spec**: 1MB chunks (spec: 256KB), width 1024 (spec: 174), raw leaves (spec: dag-pb wrapped)
- HAMT sharding for large directories uses murmur3-x64-64 hash, fanout typically 256

**DAG-PB:** Protobuf with PBNode(Data, Links) and PBLink(Hash, Name, Tsize)
- Canonical form: Links sorted by Name, Links section before Data in binary
- Hash field is binary CID (no multibase prefix)

## Design Rationale

- **CAR files** are the transport format — they package blocks for HTTP upload/download. Using a content-addressed archive means the shard itself gets a CID (`0x0202` codec) that can be referenced in the upload record
- **UnixFS** provides the standard IPFS file representation, making content retrievable by standard IPFS gateways. Using raw leaves (not dag-pb wrapped) produces canonical CIDs
- **Sharding** splits large uploads across multiple CAR files because individual HTTP requests have practical size limits. The ~127MB default matches blob storage upload limits
- **Sharded DAG Index** solves the "which shard has my block?" problem — given a content CID, the index tells you which CAR shard to fetch and at what byte offset, enabling efficient partial retrieval without downloading the whole file

## Authoritative Specs
- [CARv1 Spec](https://ipld.io/specs/transport/car/carv1/)
- [CARv2 Spec](https://ipld.io/specs/transport/car/carv2/)
- [UnixFS Spec](https://github.com/ipfs/specs/blob/main/UNIXFS.md)
- [DAG-PB Codec](https://ipld.io/specs/codecs/dag-pb/)
