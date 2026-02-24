# freeway

IPFS gateway as a Cloudflare Worker. Serves content via `/ipfs/<CID>` with UCAN-based authorization and egress tracking.

## Quick Reference

```bash
npm install
npm run test:unit        # Unit tests
npm run test:miniflare   # Miniflare integration tests
npm run test:integration # Full integration tests
npm run build            # esbuild + tsc → dist/worker.mjs
```

## Structure

```
src/
  index.js              # Entry point — composeMiddleware() builds the handler
  middleware/            # 26 composable middleware functions
    withAuthorizedSpace.js   # Authorization (finds space, checks delegation)
    withContentClaimsDagula.js # DAG traversal + block fetching
    withEgressTracker.js     # Byte counting → egress queue
    withLocator.js           # Indexing Service or Content Claims backend
    withRateLimit.js         # Rate limit check
    withGatewayIdentity.js   # Ed25519 signer for gateway
    withParsedIpfsUrl.js     # Parse CID + path from URL (in gateway-lib)
  server/
    service.js           # UCAN server (handles access/delegate for content-serve)
  capabilities/
    serve.js             # space/content/serve/transport/http capability
```

## Middleware Stack (execution order)

1-6: CDN cache, context, CORS, version, error handler, gateway identity
7-10: DID doc, delegations storage, UCAN invocation handler, HTTP method filter
11-16: URL parsing, auth token, locator, CarPark fetch, delegation stubs, rate limit
17-19: CAR block handler, **authorized space**, egress client
20-22: **egress tracker**, **DAG traversal + block fetching**
23-26: Raw handler, CAR handler, content-disposition, fixed-length stream

## Key Patterns

- **Middleware composition**: `composeMiddleware(handler, [mw1, mw2, ...])` — each adds to `ctx`
- **Authorization**: `withAuthorizedSpace` locates content, finds space, checks `space/content/serve` delegation
- **Block fetching**: `BatchingFetcher` batches up to 16 blocks per HTTP Range request to R2
- **Egress**: `TransformStream` counts bytes, queues `space/egress/record` invocation to EGRESS_QUEUE

## What Breaks If You Change Things Here

- Middleware ordering is critical — reordering can break auth or egress tracking
- `withAuthorizedSpace` logic affects which content is served/blocked
- Egress tracking affects billing (see egress-tracking-flow.md)
- Locator backend (indexing service vs content claims) controlled by feature flag
