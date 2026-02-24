# blob-fetcher

Efficient block fetching from CAR shards via byte-range requests. Used by Freeway gateway for content retrieval.

## Quick Reference

```bash
npm install
npm test               # Runs entail test runner
npx tsc --build        # Type check
```

## Structure

```
src/
  index.js             # Main exports
  fetcher/
    batching.js        # BatchingFetcher — batches up to 16 block fetches per HTTP request
    simple.js          # SimpleFetcher — one request per block
  locator.js           # Content locator interface
  api.ts               # TypeScript types
```

## Key Concept: Batching

The `BatchingFetcher` is critical for gateway performance:

1. Multiple `fetch(multihash)` calls are collected
2. Calls are batched (max 16 per HTTP request)
3. A single HTTP Range request with multiple byte ranges is sent to R2
4. Multipart response is parsed back into individual blocks

This reduces HTTP round-trips by ~16x compared to fetching blocks individually.

## Key Dependencies

- `@storacha/blob-index` — ShardedDAGIndex for block-to-byte-range mapping
- `@storacha/indexing-service-client` — Locates content via indexing service
- `@web3-storage/content-claims` — Alternative content location via claims

## What Breaks If You Change Things Here

- Batching logic changes affect gateway latency directly
- Locator interface changes affect freeway middleware
- ShardedDAGIndex format changes (from blob-index) require coordinated updates
