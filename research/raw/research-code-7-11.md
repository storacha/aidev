# Research Code Findings: Topics 7-11

## Topic 7: Pail & Distributed Data Structures

### 7.1 Pail Put/Get/Del Operations (JavaScript)

**File:** `pail/src/index.js`

The core Pail is a sharded key-value bucket stored as a Merkle DAG. Each operation traverses from root to target shard, modifies entries, and propagates CID changes back up the path.

**put** -- Traverses shard tree, finds common prefixes, creates child shards for disambiguation, and propagates new CIDs back to root:
```js
export const put = async (blocks, root, key, value) => {
  const shards = new ShardFetcher(blocks)
  const rshard = await shards.get(root)
  const path = await traverse(shards, rshard, key)
  const target = path[path.length - 1]
  const skey = key.slice(target.value.prefix.length) // key within the shard

  /** @type {API.ShardEntry} */
  let entry = [skey, value]
  const targetEntries = [...target.value.entries]
  // ... (common prefix splitting logic) ...
  const shard = Shard.withEntries(Shard.putEntry(targetEntries, entry), target.value)
  let child = await Shard.encodeBlock(shard)
  additions.push(child)
  // path is root -> target, so work backwards, propagating the new shard CID
  for (let i = path.length - 2; i >= 0; i--) {
    // ... propagate child CID into parent entries
  }
  return { root: additions[additions.length - 1].cid, additions, removals: path }
}
```

**get** -- Simple traversal + lookup:
```js
export const get = async (blocks, root, key) => {
  const shards = new ShardFetcher(blocks)
  const rshard = await shards.get(root)
  const path = await traverse(shards, rshard, key)
  const target = path[path.length - 1]
  const skey = key.slice(target.value.prefix.length)
  const entry = target.value.entries.find(([k]) => k === skey)
  if (!entry) return
  return Array.isArray(entry[1]) ? entry[1][1] : entry[1]
}
```

**del** -- Traversal + removal + parent cleanup when shards empty:
```js
export const del = async (blocks, root, key) => {
  // ...traverse to target shard, find entry...
  if (Array.isArray(entry[1])) {
    // remove the value from this link+value
    shard.entries[entryidx] = [entry[0], [entry[1][0]]]
  } else {
    shard.entries.splice(entryidx, 1)
    // if now empty, remove from parent
    while (!shard.entries.length) { /* walk up, removing empty parents */ }
  }
  // ...propagate new CIDs back to root...
}
```

**traverse** -- Recursively walks shard tree using key prefix matching:
```js
const traverse = async (shards, shard, key) => {
  for (const [k, v] of shard.value.entries) {
    if (key === k) return [shard]
    if (key.startsWith(k) && Array.isArray(v)) {
      const path = await traverse(shards, await shards.get(v[0]), key.slice(k.length))
      return [shard, ...path]
    }
  }
  return [shard]
}
```

### 7.2 Shard and ShardBlock Types

**File:** `pail/src/api.ts`

Core type definitions for the shard-based trie:
```typescript
export type ShardEntryValueValue = UnknownLink
export type ShardEntryLinkValue = [ShardLink]
export type ShardEntryLinkAndValueValue = [ShardLink, UnknownLink]

/** Single key/value entry within a shard. */
export type ShardEntry = [key: string, value: ShardEntryValueValue | ShardEntryLinkValue | ShardEntryLinkAndValueValue]

export interface Shard extends ShardConfig {
  entries: ShardEntry[]
}

export type ShardLink = Link<Shard, typeof dagCBOR.code, typeof sha256.code, 1>

export interface ShardDiff {
  additions: ShardBlockView[]
  removals: ShardBlockView[]
}
```

**File:** `pail/src/shard.js`

ShardBlock creation and encoding with dag-CBOR + SHA-256:
```js
export class ShardBlock extends Block {
  static create (options) {
    return encodeBlock(create(options))
  }
}

export const create = (options) => ({ entries: [], ...configure(options) })

export const configure = (options) => ({
  version: 1,
  keyChars: options?.keyChars ?? KeyCharsASCII,
  maxKeySize: options?.maxKeySize ?? MaxKeySize,
  prefix: options?.prefix ?? ''
})

export const encodeBlock = async value => {
  const { cid, bytes } = await encode({ value, codec: dagCBOR, hasher: sha256 })
  const block = new ShardBlock({ cid, value, bytes })
  return block
}
```

### 7.3 CRDT Merge & Diff

**File:** `pail/src/merge.js`

Merge computes diffs from a common base to each target, then replays put/del operations:
```js
export const merge = async (blocks, base, targets) => {
  const diffs = await Promise.all(targets.map(t => difference(blocks, base, t)))
  let root = base
  for (const { keys } of diffs) {
    for (const [k, v] of keys) {
      let res
      if (v[1] == null) {
        res = await del(fetcher, root, k)
      } else {
        res = await put(fetcher, root, k, v[1])
      }
      // ...track additions/removals...
      root = res.root
    }
  }
  return { root, additions: [...additions.values()], removals: [...removals.values()] }
}
```

**File:** `pail/src/diff.js`

Diff computes key-level changes (adds, updates, deletes) between two shard DAGs:
```js
export const difference = async (blocks, a, b) => {
  if (isEqual(a, b)) return { keys: [], shards: { additions: [], removals: [] } }
  const shards = new ShardFetcher(blocks)
  const [ashard, bshard] = await Promise.all([shards.get(a), shards.get(b)])
  // Compares entries; for matching keys with different shard links,
  // recurses into child shards
  // Returns: { keys: KeysDiff, shards: ShardDiff }
}
```

### 7.4 CRDT Layer (Clock-Aware Operations)

**File:** `pail/src/crdt/index.js`

The CRDT layer wraps Pail operations with Merkle clock events:
```js
export const put = async (blocks, head, key, value) => {
  // ...
  const ancestor = await findCommonAncestor(events, head)
  const aevent = await events.get(ancestor)
  let { root } = aevent.value.data

  // Replay events from common ancestor in deterministic order
  const sorted = await findSortedEvents(events, head, ancestor)
  for (const { value: event } of sorted) {
    if (event.data.type === 'put') {
      result = await Pail.put(blocks, root, event.data.key, event.data.value)
    } else if (event.data.type === 'del') {
      result = await Pail.del(blocks, root, event.data.key)
    } else if (event.data.type === 'batch') {
      // ... batch operations
    }
    root = result.root
  }

  // Apply the new operation
  const result = await Pail.put(blocks, root, key, value)
  const data = { type: 'put', root: result.root, key, value }
  const event = await EventBlock.create(data, head)
  head = await Clock.advance(blocks, head, event.cid)
  return { root: result.root, additions, removals, head, event }
}
```

**File:** `pail/src/crdt/api.ts`

Operation types:
```typescript
export type Operation = (
  | PutOperation
  | DeleteOperation
  | BatchOperation
) & { root: ShardLink }

export interface PutOperation {
  type: 'put'
  key: string
  value: UnknownLink
}
export interface DeleteOperation {
  type: 'del'
  key: string
}
export interface BatchOperation {
  type: 'batch'
  ops: Array<PutOperation | DeleteOperation>
}
```

### 7.5 Merkle Clock

**File:** `pail/src/clock/index.js`

The Merkle clock tracks causal ordering of events:
```js
export const advance = async (blocks, head, event) => {
  const events = new EventFetcher(blocks)
  const headmap = new Map(head.map(cid => [cid.toString(), cid]))
  if (headmap.has(event.toString())) return head

  // does event contain the clock?
  let changed = false
  for (const cid of head) {
    if (await contains(events, event, cid)) {
      headmap.delete(cid.toString())
      headmap.set(event.toString(), event)
      changed = true
    }
  }
  if (changed) return [...headmap.values()]

  // does clock contain the event?
  for (const p of head) {
    if (await contains(events, p, event)) return head
  }
  // concurrent / forked event -- add to head
  return head.concat(event)
}
```

**File:** `pail/src/clock/api.ts`

Event types:
```typescript
export type EventLink<T> = Link<EventView<T>>

export interface EventView<T> {
  parents: Array<EventLink<T>>
  data: T
}
```

### 7.6 Go Implementation (go-pail)

**File:** `go-pail/put.go`

Direct Go port of the JS pail put logic:
```go
func Put(ctx context.Context, blocks block.Fetcher, root ipld.Link, key string, value ipld.Link) (ipld.Link, shard.Diff, error) {
	shards := shard.NewFetcher(blocks)
	rshard, err := shards.GetRoot(ctx, root)
	// ...ASCII validation...
	path, err := traverse(ctx, shards, shard.AsBlock(rshard), key)
	target := path[len(path)-1]
	skey := key[len(target.Value().Prefix()):]
	entry := shard.NewEntry(skey, shard.NewValue(value, nil))
	// ...common prefix splitting...
	// ...propagate new CIDs back to root...
	return additions[len(additions)-1].Link(), shard.Diff{Additions: additions, Removals: path}, nil
}
```

**File:** `go-pail/shard/shard.go`

Go shard types with interface-based design:
```go
type Entry interface {
	Key() string
	Value() Value
}

type Value interface {
	Shard() ipld.Link
	Value() ipld.Link
}

type Shard interface {
	Prefix() string
	Entries() []Entry
}
```

**File:** `go-pail/clock/clock.go`

Go Merkle clock implementation:
```go
func Advance[T any](ctx context.Context, blocks block.Fetcher, dataBinder node.Binder[T], head []ipld.Link, evt ipld.Link) ([]ipld.Link, error) {
	events := event.NewFetcher(blocks, dataBinder)
	headmap := map[ipld.Link]struct{}{}
	for _, h := range head { headmap[h] = struct{}{} }
	if _, ok := headmap[evt]; ok { return head, nil }
	// does event contain the clock? (same logic as JS)
	// does clock contain the event?
	// else: concurrent event, add to head
	return append(head, evt), nil
}
```

**File:** `go-pail/crdt/crdt.go`

Go CRDT layer:
```go
func Put(ctx context.Context, blocks block.Fetcher, head []ipld.Link, key string, value ipld.Link) (Result, error) {
	// Determine effective root, replay events, put new value
	data := operation.NewPut(root, key, value)
	eblock, err := event.MarshalBlock(evt, node.UnbinderFunc[operation.Operation](operation.Unbind))
	head, err = clock.Advance(ctx, blocks, node.BinderFunc[operation.Operation](operation.Bind), head, eblock.Link())
	return Result{Diff: shard.Diff{Additions, Removals}, Root: root, Head: head, Event: eblock}, nil
}
```

### 7.7 Prolly Tree Boundaries

No evidence of prolly tree boundary/threshold/average logic was found in the Pail repos. Pail uses a deterministic prefix-trie structure (not a probabilistic B-tree). Shard splits happen based on common key prefixes, not probabilistic boundaries.

---

## Topic 8: Gateway & Retrieval (Freeway, blob-fetcher)

### 8.1 Freeway Middleware Stack

**File:** `freeway/src/index.js`

The complete middleware composition chain -- the canonical pattern for the Storacha gateway:
```js
const middleware = composeMiddleware(
  // Prepare the Context
  withCdnCache,
  withContext,
  withOptionsRequest,
  withCorsHeaders,
  withVersionHeader,
  withErrorHandler,
  withGatewayIdentity,
  withDidDocumentHandler,
  withDelegationsStorage,

  // Handle UCAN invocations (POST)
  withUcanInvocationHandler,

  // Handle Content Serve requests (GET/HEAD)
  withHttpMethods('GET', 'HEAD'),

  // Prepare context for content requests
  withParsedIpfsUrl,
  withAuthToken,
  withLocator,
  withCarParkFetch,
  withDelegationStubs,

  // Rate-limit
  withRateLimit,

  // Fetch CAR data
  withCarBlockHandler,

  // Authorize requests
  withAuthorizedSpace,

  // Track Egress
  withEgressClient,
  withEgressTracker,

  // Fetch data
  withContentClaimsDagula,
  withFormatRawHandler,
  withFormatCarHandler,

  // Prepare the Response
  withContentDispositionHeader,
  withFixedLengthStream
)
```

### 8.2 gateway-lib Middleware Pattern & composeMiddleware

**File:** `gateway-lib/src/bindings.d.ts`

The fundamental middleware type system:
```typescript
export interface Handler<C extends Context, E extends Environment = Environment> {
  (request: Request, env: E, ctx: C): Promise<Response>
}

export interface Middleware<XC extends BC, BC extends Context = Context, E extends Environment = Environment> {
  (h: Handler<XC, E>): Handler<BC, E>
}
```

**File:** `gateway-lib/src/middleware.js`

composeMiddleware uses `reduceRight` to create a nested handler chain:
```js
export function composeMiddleware (...middlewares) {
  return handler => middlewares.reduceRight((h, m) => m(h), handler)
}
```

### 8.3 Content Serve Authorization

**File:** `freeway/src/capabilities/serve.js`

The capability definition for content serving authorization:
```js
export const transportHttp = capability({
  can: 'space/content/serve/transport/http',
  with: DID,
  nb: Schema.struct({
    token: nullable(string())
  })
})
```

**File:** `freeway/src/middleware/withAuthorizedSpace.js`

Authorization flow: locate content -> find spaces -> verify delegation -> authorize:
```js
export function withAuthorizedSpace (handler) {
  return async (request, env, ctx) => {
    const { locator, dataCid } = ctx
    const locRes = await locator.locate(dataCid.multihash)
    // Filter sites with/without space
    const sitesWithSpace = locRes.ok.site.filter((site) => site.space !== undefined)
    // First space to authorize wins
    const { space: selectedSpace, delegationProofs } = await Promise.any(
      spaces.map(async (space) => {
        const result = await authorize(SpaceDID.from(space), ctx, env)
        return result.ok
      })
    )
    return handler(request, env, {
      ...ctx,
      space: skipEgressTracking ? undefined : SpaceDID.from(selectedSpace.toString()),
      locator: locator.scopeToSpaces([selectedSpace])
    })
  }
}
```

### 8.4 blob-fetcher Batching Fetcher

**File:** `blob-fetcher/src/fetcher/batching.js`

The BatchingFetcher accumulates requests and issues HTTP multipart byte-range requests:
```js
const MAX_BATCH_SIZE = 16

class BatchingFetcher {
  async fetch (digest, options) {
    const locResult = await this.#locator.locate(digest, options)
    // ...enqueue request...
    this.#scheduleBatchProcessing()
    return deferred.promise
  }

  async #processBatch () {
    // Group by shared site URL, issue multipart range request
    const headers = { Range: `bytes=${resolvedBlobs.map(r => `${r.range[0]}-${r.range[1]}`).join(',')}` }
    const res = await fetch(url, { headers })
    // Parse multipart byte range response
    for await (const chunk of res.body.pipeThrough(new MultipartByteRangeDecoder(boundary))) {
      const blob = new Blob(resolvedBlobs[i].digest, chunk.content)
      yield ({ blob, range: resolvedBlobs[i].orig })
    }
  }
}
```

**File:** `blob-fetcher/src/api.ts`

Key interfaces for content location:
```typescript
export interface Locator {
  locate (digest: MultihashDigest, options?: LocateOptions): Promise<Result<Location, FetchError>>
  scopeToSpaces(spaces: DID[]): Locator
}

export interface Fetcher {
  fetch (digest: MultihashDigest, options?: FetchOptions): Promise<Result<Blob, FetchError>>
}

export interface Location {
  digest: MultihashDigest
  site: Site[]
}

export interface Site {
  location: URL[]
  range: ByteRange
  space?: DID
}
```

### 8.5 Locator Pattern

**File:** `freeway/src/middleware/withLocator.js`

Creates a Locator using either the Indexing Service or Content Claims:
```js
export function withLocator (handler) {
  return async (request, env, ctx) => {
    const useIndexingService = isIndexingServiceEnabled(request, env)
    const client = useIndexingService
      ? new Client({ serviceURL: env.INDEXING_SERVICE_URL ? new URL(env.INDEXING_SERVICE_URL) : undefined })
      : new ContentClaimsClient({
          serviceURL: env.CONTENT_CLAIMS_SERVICE_URL ? new URL(env.CONTENT_CLAIMS_SERVICE_URL) : undefined,
          carpark: env.CARPARK
        })
    const locator = Locator.create({ client, compressed })
    return handler(request, env, { ...ctx, locator })
  }
}
```

**File:** `blob-fetcher/src/locator/index.js`

IndexingServiceLocator implements content location with caching:
```js
export class IndexingServiceLocator {
  async locate (digest) {
    let location = this.#cache.get(digest)
    if (!location) {
      const knownSlice = this.#knownSlices.get(digest)
      if (knownSlice) {
        await this.#readShard(digest, knownSlice.shardDigest, knownSlice.position)
      } else {
        await this.#readClaims(digest, this.#compressed ? 'standard_compressed' : 'standard')
        const knownSlice = this.#knownSlices.get(digest)
        if (knownSlice) await this.#readShard(digest, knownSlice.shardDigest, knownSlice.position)
      }
      location = this.#cache.get(digest)
      if (!location) return { error: new NotFoundError(digest) }
    }
    return { ok: location }
  }
}
```

### 8.6 Dagula -- DAG Traversal

**File:** `dagula/index.js`

Dagula is the DAG traversal engine that supports DFS/BFS block fetching:
```js
export class Dagula {
  async * get (cid, options = {}) {
    cid = typeof cid === 'string' ? CID.parse(cid) : cid
    yield * this.#get((Array.isArray(cid) ? cid : [cid]).map(cid => ({ cid })), options)
  }

  async * #get (selectors, options = {}) {
    const order = options.order ?? 'dfs'
    const search = order === 'dfs' ? depthFirst() : breadthFirst()
    const getLinks = blockLinks(options.filter)
    selectors = search(selectors)
    // ...fetch blocks, decode, follow links...
  }
}
```

**File:** `freeway/src/middleware/withContentClaimsDagula.js`

Dagula is wired into the gateway via the `withContentClaimsDagula` middleware:
```js
export function withContentClaimsDagula (handler) {
  return async (request, env, ctx) => {
    const { locator } = ctx
    const fetcher = BatchingFetcher.create(locator, ctx.fetch)
    const dagula = new Dagula({
      async get (cid) {
        const res = await fetcher.fetch(cid.multihash)
        return res.ok ? { cid, bytes: await res.ok.bytes() } : undefined
      },
      async stream (cid, options) {
        const res = await fetcher.fetch(cid.multihash, options)
        return res.ok ? res.ok.stream() : undefined
      },
      async stat (cid) {
        const res = await locator.locate(cid.multihash)
        return res.ok ? { size: res.ok.site[0].range.length } : undefined
      }
    })
    return handler(request, env, { ...ctx, blocks: dagula, dag: dagula, unixfs: dagula })
  }
}
```

### 8.7 Egress Tracking

**File:** `freeway/src/middleware/withEgressTracker.js`

Uses a TransformStream to count bytes and emit `space/egress/record` UCAN invocations:
```js
export function withEgressTracker (handler) {
  return async (req, env, ctx) => {
    const response = await handler(req, env, ctx)
    const responseBody = response.body.pipeThrough(
      createByteCountStream(async (totalBytesServed) => {
        if (totalBytesServed > 0) {
          const invocation = Space.egressRecord.invoke({
            issuer: ctx.gatewayIdentity,
            audience: DID.parse(env.UPLOAD_SERVICE_DID),
            with: SpaceDID.from(space),
            nb: {
              resource: ctx.dataCid,
              bytes: totalBytesServed,
              servedAt: new Date().getTime()
            },
            proofs: ctx.delegationProofs
          })
          ctx.waitUntil(env.EGRESS_QUEUE.send(dagJSON.encode({ invocation: archiveResult.ok })))
        }
      })
    )
    return new Response(responseBody, { status: response.status, headers: response.headers })
  }
}
```

---

## Topic 9: Encryption & KMS

### 9.1 UCAN-KMS Service Structure

**File:** `ucan-kms/src/api.types.ts`

Service interface for the encryption KMS:
```typescript
export interface Service {
  space: {
    encryption: {
      setup: ServiceMethod<SpaceEncryptionSetup, EncryptionSetupResult, Failure>;
      key: {
        decrypt: ServiceMethod<SpaceEncryptionKeyDecrypt, KeyDecryptResult, Failure>;
      };
    };
  };
}

export interface Context {
  ucanKmsSigner: Signer<`did:key:${string}`, any>;
  ucanKmsIdentity: Server.Verifier;
  kms: KMSService;
  revocationStatusClient: RevocationStatusClient;
  subscriptionStatusService: SubscriptionStatusService;
  ucanPrivacyValidationService: UcanPrivacyValidationService;
  kmsRateLimiter: KmsRateLimiter;
}
```

**File:** `ucan-kms/src/service.js`

UCANTO service registration pattern for encryption capabilities:
```js
export function createService (ctx, env) {
  return {
    space: {
      encryption: {
        setup: UcantoServer.provideAdvanced({
          capability: EncryptionSetup,
          audience: AudienceSchema,
          handler: async ({ capability, invocation }) => {
            // Rate limit, validate UCAN, setup KMS key
            const result = await handleEncryptionSetup(request, invocation, ctx, env)
            return result
          }
        }),
        key: {
          decrypt: UcantoServer.provideAdvanced({
            capability: EncryptionKeyDecrypt,
            audience: AudienceSchema,
            handler: async ({ capability, invocation }) => {
              // Rate limit, validate, decrypt symmetric key
              const result = await handleKeyDecryption(request, invocation, ctx, env)
              return result
            }
          })
        }
      }
    }
  }
}
```

### 9.2 Encryption Setup Handler

**File:** `ucan-kms/src/handlers/encryptionSetup.js`

Sets up RSA key pairs in Google KMS per space:
```js
export async function handleEncryptionSetup (request, invocation, ctx, env) {
  // 1. Validate UCAN invocation
  const ucanValidationResult = await ctx.ucanPrivacyValidationService.validateEncryption(invocation, request.space)
  // 2. Validate space has paid plan
  const planResult = await ctx.subscriptionStatusService.isProvisioned(request.space, proofs, ctx)
  // 3. Setup KMS key (creates or retrieves RSA key pair)
  const kmsResult = await ctx.kms.setupKeyForSpace(request, env)
  const { publicKey, algorithm, provider } = kmsResult.ok
  return ok(kmsResult.ok)
}
```

### 9.3 Key Decryption Handler

**File:** `ucan-kms/src/handlers/keyDecryption.js`

Decrypts symmetric keys that were encrypted with the space's RSA public key:
```js
export async function handleKeyDecryption (request, invocation, ctx, env) {
  // 1. Validate decrypt delegation
  const validationResult = await ctx.ucanPrivacyValidationService?.validateDecryption(invocation, request.space, ctx, env)
  // 2. Validate subscription
  const planResult = await ctx.subscriptionStatusService.isProvisioned(request.space, proofs, ctx)
  // 3. Check revocation status
  const revocationResult = await ctx.revocationStatusClient.checkStatus(proofs, request.space, env)
  // 4. Decrypt symmetric key using KMS
  const kmsResult = await ctx.kms.decryptSymmetricKey(request, env)
  return ok({ decryptedSymmetricKey: kmsResult.ok.decryptedKey })
}
```

### 9.4 Google Cloud KMS Integration

**File:** `ucan-kms/src/services/googleKms.js`

RSA asymmetric encryption via Google Cloud KMS:
```js
export class GoogleKMSService {
  async setupKeyForSpace (request, env) {
    const sanitizedKeyId = sanitizeSpaceDIDForKMSKeyId(request.space)
    const keyName = `projects/${env.GOOGLE_KMS_PROJECT_ID}/locations/${actualLocation}/keyRings/${actualKeyring}/cryptoKeys/${sanitizedKeyId}`
    // Check if key exists, create if not
    // Key purpose: ASYMMETRIC_DECRYPT, algorithm: RSA_DECRYPT_OAEP_3072_SHA256
    const createResponse = await fetch(createKeyUrl, {
      method: 'POST',
      body: JSON.stringify({
        purpose: 'ASYMMETRIC_DECRYPT',
        versionTemplate: { algorithm: 'RSA_DECRYPT_OAEP_3072_SHA256' }
      })
    })
    return ok({ publicKey, algorithm, provider: 'google-kms' })
  }

  async decryptSymmetricKey (request, env) {
    // Use asymmetricDecrypt API to decrypt the symmetric key
    const kmsUrl = `${GOOGLE_KMS_BASE_URL}/${primaryVersion}:asymmetricDecrypt`
    const response = await fetch(kmsUrl, {
      method: 'POST',
      body: JSON.stringify({ ciphertext: base64Ciphertext })
    })
    // Decode base64 result, re-encode with multibase
    return ok({ decryptedKey: base64.encode(binaryData) })
  }
}
```

### 9.5 ECDH Key Agreement (P-256)

**File:** `upload-service/packages/access-client/src/crypto/p256-ecdh.js`

ECDH key exchange using P-256 curve, deriving AES-GCM keys:
```js
export class EcdhKeypair {
  static async create() {
    const { keypair, did } = await EcdhKeypair.ecdhKey()
    return new EcdhKeypair(keypair, did)
  }

  static async ecdhKey() {
    const keypair = await webcrypto.subtle.generateKey(
      { name: 'ECDH', namedCurve: 'P-256' },
      false,
      ['deriveKey', 'deriveBits']
    )
    return { keypair, did: await didFromPubkey(keypair.publicKey) }
  }

  async deriveSharedKey(otherDid) {
    const publicKey = await ecdhKeyFromDid(otherDid)
    const key = await webcrypto.subtle.deriveKey(
      { name: 'ECDH', public: publicKey },
      this.#keypair.privateKey,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    )
    return new AesKey(key)
  }

  async encryptForDid(data, otherDid) {
    const sharedKey = await this.deriveSharedKey(otherDid)
    return sharedKey.encrypt(data)
  }
}
```

Key pattern: DID -> P-256 public key -> ECDH key agreement -> AES-GCM-256 shared key

---

## Topic 10: Go Ecosystem

### 10.1 go-ucanto Server Setup

**File:** `go-ucanto/server/server.go`

Server creation with functional options pattern:
```go
func NewServer(id principal.Signer, options ...Option) (ServerView[Service], error) {
	cfg := srvConfig{service: Service{}}
	for _, opt := range options {
		if err := opt(&cfg); err != nil { return nil, err }
	}
	codec := cfg.codec
	if codec == nil { codec = car.NewInboundCodec() }
	canIssue := cfg.canIssue
	if canIssue == nil { canIssue = validator.IsSelfIssued }
	// ...
	ctx := serverContext{id, canIssue, validateAuthorization, resolveProof, parsePrincipal, resolveDIDKey, validateTimeBounds, cfg.authorityProofs, cfg.altAudiences}
	svr := &server{id, cfg.service, ctx, codec, catch, cfg.logReceipt}
	return svr, nil
}

type Service = map[ucan.Ability]ServiceMethod[ipld.Builder, failure.IPLDBuilderFailure]

type ServiceMethod[O ipld.Builder, X failure.IPLDBuilderFailure] func(
	context.Context,
	invocation.Invocation,
	InvocationContext,
) (transaction.Transaction[O, X], error)
```

Request handling -- decode message, dispatch to capability handlers:
```go
func Run(ctx context.Context, server Server[Service], invocation ServiceInvocation) (receipt.AnyReceipt, error) {
	caps := invocation.Capabilities()
	cap := caps[0]
	handle, ok := server.Service()[cap.Can()]
	tx, err := handle(ctx, invocation, server.Context())
	rcpt, err := receipt.Issue(server.ID(), tx.Out(), ran.FromInvocation(invocation), opts...)
	return rcpt, nil
}
```

### 10.2 go-ucanto Provide (Handler Registration)

**File:** `go-ucanto/server/handler.go`

The `Provide` function wraps a typed handler with UCAN validation:
```go
func Provide[C any, O ipld.Builder, X failure.IPLDBuilderFailure](
	capability validator.CapabilityParser[C],
	handler HandlerFunc[C, O, X],
) ServiceMethod[O, failure.IPLDBuilderFailure] {
	return func(ctx context.Context, invocation invocation.Invocation, ictx InvocationContext) (transaction.Transaction[O, failure.IPLDBuilderFailure], error) {
		vctx := validator.NewValidationContext(
			ictx.ID().Verifier(), capability, ictx.CanIssue, ictx.ValidateAuthorization,
			ictx.ResolveProof, ictx.ParsePrincipal, ictx.ResolveDIDKey, ictx.ValidateTimeBounds,
			ictx.AuthorityProofs()...,
		)
		auth, aerr := validator.Access(ctx, invocation, vctx)
		res, fx, herr := handler(ctx, auth.Capability(), invocation, ictx)
		return transaction.NewTransaction(res, transaction.WithEffects(fx)), nil
	}
}
```

### 10.3 go-libstoracha Capabilities

**File:** `go-libstoracha/capabilities/blob/allocate.go`

Capability definition pattern in Go:
```go
const AllocateAbility = "blob/allocate"

type AllocateCaveats struct {
	Space did.DID
	Blob  types.Blob
	Cause ucan.Link
}

func (ac AllocateCaveats) ToIPLD() (datamodel.Node, error) {
	return ipld.WrapWithRecovery(&ac, AllocateCaveatsType(), types.Converters...)
}

var AllocateCaveatsReader = schema.Struct[AllocateCaveats](AllocateCaveatsType(), nil, types.Converters...)
var Allocate = validator.NewCapability(
	AllocateAbility,
	schema.DIDString(),
	AllocateCaveatsReader,
	validator.DefaultDerives,
)
```

Available capability packages:
```
access, account, assert, blob, claim, consumer, filecoin, http,
pdp, provider, space, types, ucan, upload, web3.storage
```

### 10.4 Go Service Entry Points

**File:** `indexing-service/cmd/main.go`

Indexing service uses urfave/cli:
```go
func main() {
	app := &cli.App{
		Name:  "indexing-service",
		Usage: "Manage running the indexing service.",
		Commands: []*cli.Command{
			serverCmd, awsCmd, queryCmd,
		},
	}
	if err := app.Run(os.Args); err != nil { log.Fatal(err) }
}
```

**File:** `piri/cmd/cli/root.go`

Piri uses cobra/viper:
```go
var rootCmd = &cobra.Command{
	Use:   "piri",
	Short: piriShortDescription,
	Long:  "Piri - Provable Information Retention Interface...",
}

func init() {
	rootCmd.AddCommand(serve.Cmd)
	rootCmd.AddCommand(wallet.Cmd)
	rootCmd.AddCommand(identity.Cmd)
	rootCmd.AddCommand(delegate.Cmd)
	rootCmd.AddCommand(client.Cmd)
	rootCmd.AddCommand(status.Cmd)
	rootCmd.AddCommand(setup.InitCmd)
	rootCmd.AddCommand(setup.InstallCmd)
}
```

**File:** `indexing-service/cmd/server.go`

Server construction with go-ucanto:
```go
var id principal.Signer
id, err = ed25519.Parse(cCtx.String("private-key"))
opts = append(opts, server.WithIdentity(id))
presolv, _ := principalresolver.New(presets.PrincipalMapping)
opts = append(opts, server.WithContentClaimsOptions(
    userver.WithPrincipalResolver(presolv.ResolveDIDKey),
))
indexer, _ := construct.Construct(sc)
indexer.Startup(cCtx.Context)
server.ListenAndServe(addr, indexer, opts...)
```

**File:** `piri/cmd/lambda/putblob/main.go`

Lambda entry point for Piri blob operations:
```go
func main() {
	lambda.StartHTTPHandler(makeHandler)
}

func makeHandler(cfg aws.Config) (http.Handler, error) {
	service, err := aws.Construct(cfg)
	handler := blobs.NewBlobPutHandler(
		service.Blobs().Presigner(),
		service.Blobs().Allocations(),
		service.Blobs().Store(),
	)
	return telemetry.NewErrorReportingHandler(func(w http.ResponseWriter, r *http.Request) error {
		return handler(aws.NewHandlerContext(w, r))
	}), nil
}
```

---

## Topic 11: libp2p & Networking

### 11.1 libp2p Host Creation

**File:** `storetheindex/command/daemon.go`

The storetheindex daemon creates a libp2p host for P2P ingestion:
```go
p2pmaddr, err := multiaddr.NewMultiaddr(p2pAddr)
p2pOpts := []libp2p.Option{
    // Use the keypair generated during init
    libp2p.Identity(privKey),
    // Listen at specific address
    libp2p.ListenAddrs(p2pmaddr),
}
if cfg.Addresses.NoResourceManager {
    p2pOpts = append(p2pOpts, libp2p.ResourceManager(&network.NullResourceManager{}))
}
p2pHost, err = libp2p.New(p2pOpts...)
defer p2pHost.Close()

// Initialize ingester with p2p host
ingester, err = ingest.NewIngester(cfg.Ingest, p2pHost, indexer, reg, dstore, dsTmp)

// Bootstrap to gossip mesh
if len(cfg.Bootstrap.Peers) != 0 && cfg.Bootstrap.MinimumPeers != 0 {
    addrs, _ := cfg.Bootstrap.PeerAddrs()
    // connect to minimum peers for gossip mesh participation
}
```

### 11.2 Pubsub / GossipSub Usage

**File:** `storetheindex/internal/ingest/ingest.go`

The storetheindex ingester uses libp2p for advertisement syncing. The pubsub configuration is managed through `go-libipni` announce/dagsync libraries:
```go
import (
    "github.com/ipni/go-libipni/announce"
    "github.com/ipni/go-libipni/dagsync"
    "github.com/libp2p/go-libp2p/core/host"
    "github.com/libp2p/go-libp2p/core/peer"
    "github.com/multiformats/go-multiaddr"
)
```

GossipSub configuration lives in `storetheindex/config/ingest.go` and `config/bootstrap.go` -- the Ingester subscribes to advertisement announcements via libp2p gossipsub topics.

### 11.3 Multiaddr Usage

**File:** `indexing-service/cmd/server.go`

Multiaddr is used in the indexing service for IPNI endpoint configuration:
```go
import (
    "github.com/ipni/go-libipni/maurl"
    "github.com/multiformats/go-multiaddr"
)

func ipniOpts(ipniFormatPeerID string, ipniFormatEndpoint string) ([]server.Option, error) {
    peerID, err := peer.Decode(ipniFormatPeerID)
    url, err := url.Parse(ipniFormatEndpoint)
    ma, err := maurl.FromURL(url)
    return []server.Option{
        server.WithIPNI(peer.AddrInfo{ID: peerID, Addrs: []multiaddr.Multiaddr{ma}}, metadata.Default.New(metadata.IpfsGatewayHttp{})),
    }, nil
}
```

### 11.4 Bitswap

**File:** `indexing-service/pkg/service/providerindex/providerindex_test.go`

Bitswap metadata is used in the indexing service for provider results:
```go
// Bitswap metadata appears in provider index tests for IPNI integration
```

**File:** `go-libstoracha/testutil/gen.go`

Bitswap metadata generation in test utilities.

Note: Bitswap is referenced primarily in metadata/protocol handling rather than as a direct transfer protocol. The primary retrieval path in Storacha uses HTTP byte-range requests, not Bitswap.

### 11.5 DHT/Routing

No direct DHT usage (`dht.New`, `FindProviders`) was found in the Storacha Go repos. Content routing is handled through IPNI (InterPlanetary Network Indexer) rather than a DHT. The `storetheindex` repo is the IPNI implementation itself, which uses:
- HTTP advertisement ingestion
- libp2p gossipsub for advertisement announcements
- Direct HTTP queries for content routing (via `cid.contact`)

### 11.6 Key Repos Summary

| Repo | Language | Role | CLI Framework |
|------|----------|------|---------------|
| indexing-service | Go | Content routing/indexing | urfave/cli |
| piri | Go | Storage provider node | cobra/viper |
| storetheindex | Go | IPNI indexer (forked) | urfave/cli |
| go-ucanto | Go | UCAN RPC framework | (library) |
| go-libstoracha | Go | Shared capabilities | (library) |
| go-pail | Go | KV bucket data structure | (library) |

---

## Summary of Key Patterns

### Pail Architecture
- **Trie-based sharding**: Keys are split by common prefixes into child shards
- **Merkle DAG**: Every shard is a dag-CBOR block; changes propagate CIDs up to root
- **CRDT via Merkle Clock**: Each mutation creates an event with parent links; concurrent events create multi-headed clocks; resolution replays events from common ancestor in deterministic order
- **Identical JS/Go implementations**: Same algorithm in both languages

### Gateway Architecture
- **Middleware composition**: `composeMiddleware(...fns)` creates a handler chain via `reduceRight`
- **Authorization flow**: Locate content -> find spaces -> verify `space/content/serve/transport/http` delegations
- **Batched retrieval**: `BatchingFetcher` groups requests by site URL, uses HTTP multipart byte-range requests
- **DAG traversal**: `Dagula` provides DFS/BFS block traversal backed by the batching fetcher

### Encryption Architecture
- **RSA asymmetric keys per space**: Google Cloud KMS manages RSA-OAEP-3072 keys
- **Two capabilities**: `space/encryption/setup` creates/retrieves keys; `space/encryption/key/decrypt` decrypts symmetric keys
- **Client-side ECDH**: P-256 ECDH key agreement derives AES-GCM-256 shared keys for peer-to-peer encryption

### Go Ecosystem
- **go-ucanto**: Server with `Service = map[Ability]ServiceMethod`, `Provide()` wraps handlers with UCAN validation
- **go-libstoracha**: Capability definitions use IPLD schema types with `validator.NewCapability()`
- **Service patterns**: Lambda handlers via `lambda.StartHTTPHandler()`, CLI servers via cobra/urfave
- **No DHT**: Content routing through IPNI HTTP, not Kademlia DHT
