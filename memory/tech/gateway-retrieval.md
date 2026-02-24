<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Gateway & Retrieval: Patterns & Reference

> **TL;DR:** Freeway is a Cloudflare Worker gateway with 26 composable middlewares. It parses IPFS URLs, locates content via the Indexing Service (IPNI + claims), authorizes via `space/content/serve` delegations, fetches blocks using BatchingFetcher (batches up to 16 byte-range requests per HTTP call to R2), traverses DAGs with Dagula, and tracks egress for billing via Cloudflare Queues. Response formats: raw block, CAR stream, or UnixFS file.

> Concepts: Freeway middleware (P0), content serve auth (P0), blob-fetcher batching (P0), Dagula DAG traversal (P1), egress tracking (P1)
> Key repos: freeway, gateway-lib, blob-fetcher, hoverboard, dagula

## How Retrieval Works

```
HTTP GET /ipfs/<CID>/path
    │
    v
Freeway (Cloudflare Worker)
    │
    ├── Parse IPFS URL → extract CID + path
    ├── Create Locator (Indexing Service or Content Claims)
    ├── Locate content → find spaces that have it
    ├── Authorize → verify space/content/serve delegation
    ├── Track egress → count bytes, queue billing record
    ├── Create Dagula (DAG traverser) backed by BatchingFetcher
    ├── Traverse DAG from root CID following path
    │     └── For each block needed:
    │           BatchingFetcher.fetch(multihash)
    │             → Locator.locate(multihash) → byte range in shard
    │             → HTTP range request to R2 → block bytes
    └── Return response (raw block, CAR stream, or UnixFS file)
```

## Patterns

### Pattern: Freeway middleware composition
**When:** Understanding or extending the gateway request pipeline
**Template:**
```js
import { composeMiddleware } from '@web3-storage/gateway-lib/middleware'

const middleware = composeMiddleware(
  // Phase 1: Context setup
  withCdnCache,
  withContext,
  withOptionsRequest,
  withCorsHeaders,
  withVersionHeader,
  withErrorHandler,
  withGatewayIdentity,
  withDelegationsStorage,

  // Phase 2: UCAN invocation handling (POST requests)
  withUcanInvocationHandler,

  // Phase 3: Content serve (GET/HEAD)
  withHttpMethods('GET', 'HEAD'),
  withParsedIpfsUrl,
  withAuthToken,
  withLocator,
  withCarParkFetch,
  withDelegationStubs,
  withRateLimit,
  withCarBlockHandler,
  withAuthorizedSpace,
  withEgressClient,
  withEgressTracker,
  withContentClaimsDagula,
  withFormatRawHandler,
  withFormatCarHandler,
  withContentDispositionHeader,
  withFixedLengthStream,
)

export default { fetch: middleware(notFound) }
```
**Key files:** `freeway/src/index.js`
**Gotchas:**
- `composeMiddleware` uses `reduceRight` — middlewares execute left to right (first added = outermost)
- Each middleware takes a handler and returns a handler: `(handler) => (request, env, ctx) => Response`
- Context (`ctx`) is progressively enriched by each middleware

### Pattern: Middleware implementation
**When:** Writing a new gateway middleware
**Template:**
```js
// Middleware type: (Handler<ExtendedCtx>) => Handler<BaseCtx>
export function withMyFeature(handler) {
  return async (request, env, ctx) => {
    // 1. Do pre-processing, enrich context
    const myData = await computeSomething(env)

    // 2. Call next handler with enriched context
    const response = await handler(request, env, { ...ctx, myData })

    // 3. Optional: post-process response
    return new Response(response.body, {
      headers: { ...response.headers, 'X-My-Header': 'value' },
    })
  }
}
```
**Key files:** `gateway-lib/src/middleware.js`, `freeway/src/middleware/`

### Pattern: Content location resolution
**When:** Finding where content is stored
**Template:**
```js
// Locator interface:
const locResult = await locator.locate(cid.multihash)
// locResult.ok = { digest, site: [{ location: [URL], range: { offset, length }, space?: DID }] }

// Two backends:
// 1. Indexing Service (preferred): queries IPNI + content claims
const client = new IndexingServiceClient({ serviceURL })
// 2. Content Claims (fallback): queries claims directly
const client = new ContentClaimsClient({ serviceURL, carpark })

const locator = Locator.create({ client })
```
**Key files:** `freeway/src/middleware/withLocator.js`, `blob-fetcher/src/locator/index.js`

### Pattern: Batch byte-range fetching
**When:** Efficiently fetching multiple blocks from the same blob
**Template:**
```js
import { BatchingFetcher } from '@web3-storage/blob-fetcher'

const fetcher = BatchingFetcher.create(locator)

// Individual fetches are batched automatically (max 16 per batch):
const result = await fetcher.fetch(digest)
// result.ok = Blob with .bytes() and .stream() methods

// Under the hood:
// 1. Requests accumulate in a microtask queue
// 2. Grouped by shared blob URL
// 3. Single HTTP request with multipart byte-range: Range: bytes=0-128,129-256,...
// 4. Multipart response parsed, individual results returned
```
**Key files:** `blob-fetcher/src/fetcher/batching.js`
**Gotchas:**
- Max batch size: 16 requests per HTTP request
- Uses HTTP multipart byte-range responses (RFC 2616)
- Batching is transparent — callers just call `fetch(digest)` and batching happens automatically

### Pattern: Content serve authorization
**When:** Checking if a gateway request is authorized to serve content from a space
**Template:**
```js
// The capability:
// space/content/serve/transport/http
//   with: space DID
//   nb: { token?: string }

// Authorization flow in middleware:
// 1. Locate content → get sites with space info
const locRes = await locator.locate(dataCid.multihash)
const sitesWithSpace = locRes.ok.site.filter(s => s.space !== undefined)

// 2. For each space, check delegation
const { space, delegationProofs } = await Promise.any(
  spaces.map(async space => {
    const result = await authorize(SpaceDID.from(space), ctx, env)
    return result.ok
  })
)
// First space to authorize wins
```
**Key files:** `freeway/src/middleware/withAuthorizedSpace.js`, `freeway/src/capabilities/serve.js`

### Pattern: Egress tracking
**When:** Counting bytes served for billing
**Template:**
```js
// Uses a TransformStream to count bytes flowing through:
const responseBody = response.body.pipeThrough(
  createByteCountStream(async (totalBytesServed) => {
    if (totalBytesServed > 0) {
      const invocation = Space.egressRecord.invoke({
        issuer: gatewayIdentity,
        audience: uploadServiceDID,
        with: spaceDID,
        nb: { resource: dataCid, bytes: totalBytesServed, servedAt: Date.now() },
        proofs: delegationProofs,
      })
      // Queue the invocation for async processing
      ctx.waitUntil(env.EGRESS_QUEUE.send(dagJSON.encode({ invocation: archive })))
    }
  })
)
```
**Key files:** `freeway/src/middleware/withEgressTracker.js`

### Pattern: DAG traversal with Dagula
**When:** Traversing a content DAG to retrieve blocks
**Template:**
```js
import { Dagula } from 'dagula'

const dagula = new Dagula({
  async get(cid) {
    const res = await fetcher.fetch(cid.multihash)
    return res.ok ? { cid, bytes: await res.ok.bytes() } : undefined
  },
  async stream(cid, options) {
    const res = await fetcher.fetch(cid.multihash, options)
    return res.ok ? res.ok.stream() : undefined
  },
})

// DFS traversal (default):
for await (const block of dagula.get(rootCID)) {
  // block = { cid, bytes }
}
// BFS:
for await (const block of dagula.get(rootCID, { order: 'bfs' })) { }
```
**Key files:** `dagula/index.js`, `freeway/src/middleware/withContentClaimsDagula.js`

## Key Interfaces

```typescript
// gateway-lib types
interface Handler<C, E> { (request: Request, env: E, ctx: C): Promise<Response> }
interface Middleware<XC, BC, E> { (h: Handler<XC, E>): Handler<BC, E> }

// blob-fetcher types
interface Locator {
  locate(digest: MultihashDigest, options?: LocateOptions): Promise<Result<Location>>
  scopeToSpaces(spaces: DID[]): Locator
}
interface Fetcher {
  fetch(digest: MultihashDigest, options?: FetchOptions): Promise<Result<Blob>>
}
interface Location { digest: MultihashDigest, site: Site[] }
interface Site { location: URL[], range: ByteRange, space?: DID }
```

## Key Files Index

| Role | File |
|------|------|
| Freeway entry point | `freeway/src/index.js` |
| composeMiddleware | `gateway-lib/src/middleware.js` |
| Middleware types | `gateway-lib/src/bindings.d.ts` |
| Content serve capability | `freeway/src/capabilities/serve.js` |
| Auth middleware | `freeway/src/middleware/withAuthorizedSpace.js` |
| Locator middleware | `freeway/src/middleware/withLocator.js` |
| Egress tracking | `freeway/src/middleware/withEgressTracker.js` |
| Dagula integration | `freeway/src/middleware/withContentClaimsDagula.js` |
| BatchingFetcher | `blob-fetcher/src/fetcher/batching.js` |
| Locator (Indexing Service) | `blob-fetcher/src/locator/index.js` |
| Dagula DAG traversal | `dagula/index.js` |
| Blockstore (gateway) | `hoverboard/src/blocks.js` |
| CAR response handler | `gateway-lib/src/handlers/car.js` |

## Design Rationale

- **Middleware composition**: Cloudflare Workers architecture makes middleware composition natural — each layer adds context or processing without coupling
- **BatchingFetcher**: Individual block fetches would be N HTTP requests; batching collapses them into N/16 multipart range requests — critical for performance since blocks within the same shard are physically adjacent in R2
- **Two locator backends**: Indexing Service is the newer, richer path (IPNI + claims); Content Claims is the legacy fallback. The `withLocator` middleware switches based on config
- **Space-scoped authorization**: Content is served from spaces; the gateway checks for `space/content/serve/transport/http` delegation. No client-side UCAN needed for HTTP GET — the gateway self-authorizes using stored delegation stubs
- **Egress via queue**: Byte counting is non-blocking — the record is queued to Cloudflare Queues and processed asynchronously by the upload service for billing

## Authoritative Specs
- [IPFS Gateway Spec](https://specs.ipfs.tech/http-gateways/)
- [Trustless Gateway Spec](https://specs.ipfs.tech/http-gateways/trustless-gateway/)
- [Content Serve Auth Spec](https://github.com/storacha/specs/blob/main/content-serve-auth.md)
- [Freeway Source](https://github.com/storacha/freeway)
