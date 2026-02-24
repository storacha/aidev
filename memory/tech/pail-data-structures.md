<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Pail & Distributed Data Structures: Patterns & Reference

> **TL;DR:** Pail is a sharded key-value store implemented as a prefix trie (NOT a prolly tree) over a Merkle DAG. Every mutation returns a new root CID (immutable). The CRDT layer wraps operations in Merkle clock events for concurrent-safe merge across replicas. Used for space content listings and upload metadata. JS: `@web3-storage/pail`, Go: `github.com/storacha/go-pail`. w3clock service provides persistent clock state via Cloudflare Durable Objects.

> Concepts: Pail key-value store (P0), shard-based trie (P0), CRDT merge (P0), Merkle clock (P0)
> Key repos: pail, go-pail, w3clock

## How Pail Works

Pail is a sharded key-value bucket stored as a Merkle DAG. It's a **prefix trie** (NOT a prolly tree) where:
- Each shard is a dag-cbor block containing entries: `[key_suffix, value_or_link]`
- Shards split when keys share a common prefix — the prefix becomes a child shard
- Every mutation returns a new root CID (immutable DAG)
- The CRDT layer wraps mutations in Merkle clock events for concurrent merge

```
Root shard (prefix="")
├── ["a", CID_of_value_a]           ← direct value
├── ["b", [CID_of_child_shard_b]]   ← link to child shard
│     └── Child shard (prefix="b")
│         ├── ["ar", CID_of_value_bar]
│         └── ["az", CID_of_value_baz]
└── ["c", [CID_of_child_shard_c, CID_of_value_c]]  ← link + value
```

## Patterns

### Pattern: Put a key-value pair
**When:** Adding or updating a value in the Pail
**Template:**
```js
import { put } from '@web3-storage/pail'

const { root: newRoot, additions, removals } = await put(blocks, rootCID, 'mykey', valueCID)
// root: new root shard CID
// additions: new shard blocks to store
// removals: old shard blocks that were replaced
```
**Under the hood:**
1. Traverse from root to target shard using key prefix matching
2. Find or create entry in target shard
3. If key shares prefix with existing entry → create child shard for disambiguation
4. Propagate new CIDs back up the path to root
**Key files:** `pail/src/index.js`

### Pattern: Get a value by key
**When:** Looking up a value
**Template:**
```js
import { get } from '@web3-storage/pail'
const value = await get(blocks, rootCID, 'mykey')  // → CID or undefined
```
**Key files:** `pail/src/index.js`

### Pattern: CRDT put (concurrent-safe)
**When:** Multiple writers may be operating concurrently
**Template:**
```js
import * as CRDT from '@web3-storage/pail/crdt'

const { root, head, event, additions, removals } = await CRDT.put(blocks, head, 'mykey', valueCID)
// head: array of event CIDs (multi-head for concurrent events)
// event: the new clock event block (store it!)
```
**Under the hood:**
1. Find common ancestor of all heads
2. Replay events from ancestor in deterministic order (weight + CID sort)
3. Apply the new put operation
4. Create an event block wrapping the operation
5. Advance the Merkle clock
**Key files:** `pail/src/crdt/index.js`

### Pattern: Merge concurrent heads
**When:** Resolving concurrent writes from different replicas
**Template:**
```js
import { merge } from '@web3-storage/pail/merge'

const { root, additions, removals } = await merge(blocks, baseRoot, [target1Root, target2Root])
// Computes diffs from base to each target, then replays all operations
```
**Key files:** `pail/src/merge.js`, `pail/src/diff.js`

### Pattern: Advance the Merkle clock
**When:** Recording a new causal event
**Template:**
```js
import * as Clock from '@web3-storage/pail/clock'

const newHead = await Clock.advance(blocks, currentHead, newEventCID)
// Three outcomes:
// 1. Event is ancestor of head → head unchanged (already included)
// 2. Head is ancestor of event → event replaces head
// 3. Neither → concurrent fork, both added to head array
```
**Key files:** `pail/src/clock/index.js`
**Gotchas:**
- Head is an ARRAY of CIDs — multiple heads means concurrent forks
- `contains(events, a, b)` uses BFS to check if event `a` is an ancestor of `b`
- Concurrent events result in multi-headed clock until merge resolves them

### Pattern: Pail operations in Go
**When:** Using Pail from Go services
**Template:**
```go
import "github.com/storacha/go-pail"

newRoot, diff, err := pail.Put(ctx, blocks, rootLink, "key", valueLink)
value, err := pail.Get(ctx, blocks, rootLink, "key")

// CRDT operations:
import "github.com/storacha/go-pail/crdt"
result, err := crdt.Put(ctx, blocks, head, "key", valueLink)
// result.Root, result.Head, result.Event, result.Diff
```
**Key files:** `go-pail/put.go`, `go-pail/get.go`, `go-pail/crdt/crdt.go`, `go-pail/clock/clock.go`

## Key Types

```typescript
// JS Types (pail/src/api.ts)
type ShardEntry = [key: string, value: ShardEntryValue]
type ShardEntryValue = UnknownLink                    // direct value
                     | [ShardLink]                     // link to child shard
                     | [ShardLink, UnknownLink]        // link + value

interface Shard { entries: ShardEntry[], prefix: string, version: 1 }
type ShardLink = Link<Shard, typeof dagCBOR.code>

// Event types (clock)
interface EventView<T> { parents: EventLink<T>[], data: T }
type Operation = (PutOperation | DeleteOperation | BatchOperation) & { root: ShardLink }
```

```go
// Go Types (go-pail/shard/shard.go)
type Entry interface { Key() string; Value() Value }
type Value interface { Shard() ipld.Link; Value() ipld.Link }
type Shard interface { Prefix() string; Entries() []Entry }
```

## Key Files Index

| Role | File |
|------|------|
| Core put/get/del (JS) | `pail/src/index.js` |
| Shard types + encoding | `pail/src/shard.js`, `pail/src/api.ts` |
| Traverse (prefix trie walk) | `pail/src/index.js` (traverse fn) |
| CRDT operations (JS) | `pail/src/crdt/index.js` |
| Merge algorithm | `pail/src/merge.js` |
| Diff computation | `pail/src/diff.js` |
| Merkle clock (JS) | `pail/src/clock/index.js`, `pail/src/clock/api.ts` |
| Core put/get (Go) | `go-pail/put.go`, `go-pail/get.go` |
| CRDT (Go) | `go-pail/crdt/crdt.go` |
| Clock (Go) | `go-pail/clock/clock.go` |
| Shard types (Go) | `go-pail/shard/shard.go` |
| w3clock capabilities | `w3clock/src/capabilities.js` |

## Design Rationale

- **Prefix trie, NOT prolly tree**: Pail uses deterministic prefix-based splitting, not probabilistic boundaries. This makes shard structure predictable from the keys alone.
- **Immutable DAG**: Every mutation returns a new root CID — the entire history is preserved and content-addressable. Old roots remain valid as long as their blocks exist.
- **CRDT for concurrency**: The Merkle clock + deterministic replay approach means any two replicas that see the same events will converge to the same state, regardless of order.
- **Used for**: Space content listings, upload metadata — anywhere Storacha needs a mutable, mergeable key-value index backed by content-addressed storage.

## Authoritative Specs
- [Pail Source](https://github.com/storacha/pail)
- [Merkle-CRDT Paper](https://research.protocol.ai/publications/merkle-crdts/)
- [Prolly Trees (informal)](https://docs.dolthub.com/architecture/storage-engine/prolly-tree)
