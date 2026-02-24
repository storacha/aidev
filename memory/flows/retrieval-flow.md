<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Retrieval Flow: End-to-End Trace

> **TL;DR:** `GET /ipfs/<CID>` hits Freeway (CF Worker) which runs 26 middlewares: parse URL -> create Locator (Indexing Service or Content Claims) -> authorize via `space/content/serve` delegation -> create BatchingFetcher + Dagula -> traverse DAG fetching blocks via batched byte-range requests to R2 -> format response (raw/CAR/UnixFS) -> track egress bytes via Cloudflare Queue for billing. Key file: `freeway/src/index.js`.

## Overview

```
GET /ipfs/<CID>[/path]
    │
    ├── Phase 1: Context Setup (CDN cache, CORS, error handling, identity)
    ├── Phase 2: UCAN Invocation (POST requests only)
    ├── Phase 3: Content Serve (GET/HEAD)
    │     ├── Parse IPFS URL → extract CID + path
    │     ├── Create Locator (Indexing Service or Content Claims)
    │     ├── Rate limit check
    │     ├── Authorize → find space, verify content/serve delegation
    │     ├── Track egress
    │     ├── Create Dagula + BatchingFetcher
    │     ├── Traverse DAG, fetch blocks via byte-range requests to R2
    │     └── Format response (raw block, CAR stream, or UnixFS file)
    └── Return response with caching headers
```

## Middleware Stack (in execution order)

| # | Middleware | File | Context Added | External Calls |
|---|-----------|------|--------------|----------------|
| 1 | `withCdnCache` | `gateway-lib/src/middleware/` | CDN caching layer | Cloudflare CDN |
| 2 | `withContext` | `gateway-lib/src/middleware/` | Base context object | — |
| 3 | `withOptionsRequest` | `gateway-lib/src/middleware/` | Handles CORS preflight | — |
| 4 | `withCorsHeaders` | `gateway-lib/src/middleware/` | CORS headers | — |
| 5 | `withVersionHeader` | `gateway-lib/src/middleware/` | `X-Version` header | — |
| 6 | `withErrorHandler` | `gateway-lib/src/middleware/` | Error boundary | — |
| 7 | `withGatewayIdentity` | `freeway/src/middleware/` | `ctx.gatewayIdentity` (Ed25519 signer) | — |
| 8 | `withDidDocumentHandler` | `freeway/src/middleware/` | DID document endpoint | — |
| 9 | `withDelegationsStorage` | `freeway/src/middleware/` | `ctx.delegationsStorage` | R2 bucket |
| 10 | `withUcanInvocationHandler` | `freeway/src/middleware/` | Handles POST (UCAN invocations) | ucanto server |
| 11 | `withHttpMethods('GET','HEAD')` | `gateway-lib/src/middleware/` | Filter to GET/HEAD only | — |
| 12 | `withParsedIpfsUrl` | `gateway-lib/src/middleware/` | `ctx.dataCid`, `ctx.path` | — |
| 13 | `withAuthToken` | `freeway/src/middleware/` | `ctx.authToken` from query/header | — |
| 14 | `withLocator` | `freeway/src/middleware/` | `ctx.locator` (Indexing or Claims) | — |
| 15 | `withCarParkFetch` | `freeway/src/middleware/` | Direct R2 fetch for known CARs | R2 |
| 16 | `withDelegationStubs` | `freeway/src/middleware/` | Loads stored delegations | R2 |
| 17 | `withRateLimit` | `freeway/src/middleware/` | Rate limit check | Rate limit API |
| 18 | `withCarBlockHandler` | `freeway/src/middleware/` | Fast path for CAR block requests | — |
| 19 | `withAuthorizedSpace` | `freeway/src/middleware/` | `ctx.space`, `ctx.delegationProofs` | Indexing Service |
| 20 | `withEgressClient` | `freeway/src/middleware/` | `ctx.egressClient` | — |
| 21 | `withEgressTracker` | `freeway/src/middleware/` | Byte counting stream | Egress queue |
| 22 | `withContentClaimsDagula` | `freeway/src/middleware/` | `ctx.blocks`, `ctx.dag`, `ctx.unixfs` | Indexing Service, R2 |
| 23 | `withFormatRawHandler` | `gateway-lib/src/handlers/` | Raw block response | — |
| 24 | `withFormatCarHandler` | `gateway-lib/src/handlers/` | CAR stream response | — |
| 25 | `withContentDispositionHeader` | `gateway-lib/src/middleware/` | Content-Disposition header | — |
| 26 | `withFixedLengthStream` | `gateway-lib/src/middleware/` | Content-Length header | — |

## Key Steps in Detail

### URL Parsing (Step 12)
```
GET /ipfs/bafyROOT/images/photo.jpg
→ ctx.dataCid = CID.parse("bafyROOT")
→ ctx.path = "/images/photo.jpg"
```

### Locator Creation (Step 14)
- Feature flag determines backend: `isIndexingServiceEnabled(request, env)`
- **Indexing Service** (preferred): `new Client({ serviceURL })` → queries IPNI + content claims
- **Content Claims** (fallback): `new ContentClaimsClient({ serviceURL, carpark })` → direct claim lookup

### Authorization (Step 19)
```
File: freeway/src/middleware/withAuthorizedSpace.js

1. locator.locate(dataCid.multihash) → sites with space info
2. Filter sites with space: sitesWithSpace = sites.filter(s => s.space !== undefined)
3. For each space, check authorization:
   Promise.any(spaces.map(space => authorize(space, ctx, env)))
4. authorize() checks for space/content/serve/transport/http delegation
5. First space to authorize wins
6. ctx.locator scoped to authorized space
```

**Legacy spaces** (pre-auth): served without authorization check.

### Block Fetching (Step 22)
```
File: freeway/src/middleware/withContentClaimsDagula.js

1. BatchingFetcher.create(locator, ctx.fetch) → batching fetcher
2. new Dagula({ get, stream, stat }) backed by batching fetcher
3. For each block needed during traversal:
   fetcher.fetch(cid.multihash)
   → locator.locate(multihash) → byte range in shard
   → Requests batched (max 16 per HTTP request)
   → HTTP Range request to R2: Range: bytes=0-128,129-256,...
   → Multipart response parsed → individual blocks returned
```

### Egress Tracking (Step 21)
```
File: freeway/src/middleware/withEgressTracker.js

1. Wraps response.body in TransformStream that counts bytes
2. When stream completes (all bytes sent):
   - Creates space/egress/record UCAN invocation
   - Queues to EGRESS_QUEUE via ctx.waitUntil
   - See egress-tracking-flow.md for downstream processing
```

### Response Formatting (Steps 23-24)
- **Raw** (`?format=raw` or `Accept: application/vnd.ipld.raw`): Single block bytes
- **CAR** (`?format=car` or `Accept: application/vnd.ipld.car`): Streaming CAR with all blocks
- **Default**: UnixFS file content with appropriate Content-Type

## Infrastructure

| Component | Service | Purpose |
|-----------|---------|---------|
| Freeway | Cloudflare Worker | Gateway entry point |
| R2 | Cloudflare R2 | Blob storage (CAR shards) |
| Indexing Service | Go HTTP service | Content routing (IPNI + claims) |
| Content Claims | JS service | Claim storage and serving |
| CDN | Cloudflare CDN | Response caching |
| Egress Queue | Cloudflare Queue | Async egress record processing |
| Delegations Store | R2 bucket | Stored content-serve delegations |

## Key Files

| Role | File |
|------|------|
| Gateway entry | `freeway/src/index.js` |
| Authorization | `freeway/src/middleware/withAuthorizedSpace.js` |
| Locator | `freeway/src/middleware/withLocator.js` |
| DAG traversal | `freeway/src/middleware/withContentClaimsDagula.js` |
| Egress tracking | `freeway/src/middleware/withEgressTracker.js` |
| Batch fetcher | `blob-fetcher/src/fetcher/batching.js` |
| Dagula engine | `dagula/index.js` |
| Raw handler | `gateway-lib/src/handlers/block.js` |
| CAR handler | `gateway-lib/src/handlers/car.js` |
| composeMiddleware | `gateway-lib/src/middleware.js` |
