# gateway-lib

Shared library of middleware and handlers for IPFS gateways. Used by Freeway and potentially other gateway implementations.

## Quick Reference

```bash
npm install
node --test test/**/*.spec.js    # Run tests
npm run build:types              # Build TypeScript declarations
```

## Structure

```
src/
  index.js             # Main exports
  middleware.js         # composeMiddleware() function
  middleware/
    withCdnCache.js        # CDN caching layer
    withContext.js          # Base context setup
    withCorsHeaders.js     # CORS headers
    withOptionsRequest.js  # CORS preflight
    withParsedIpfsUrl.js   # Parse /ipfs/<CID>/path → ctx.dataCid, ctx.path
    withHttpMethods.js     # Filter by HTTP method
    withContentDispositionHeader.js
    withFixedLengthStream.js
    withVersionHeader.js
    withErrorHandler.js
  handlers/
    block.js           # Raw block response (format=raw)
    car.js             # CAR stream response (format=car)
```

## Key Concepts

- **composeMiddleware**: `composeMiddleware(innerHandler, [mw1, mw2, ...])` — processes left to right, each middleware wraps the next
- **Context accumulation**: Each middleware adds fields to `ctx` object
- **Response formats**: Raw (single block), CAR (streaming), UnixFS (default file content)

## What Breaks If You Change Things Here

- Middleware interface changes affect Freeway (primary consumer)
- URL parsing changes affect all content routing
- Response handler changes affect client-visible content format
