# content-claims

Content claims storage and serving. Stores and retrieves 6 types of content claims as UCAN delegations.

## Quick Reference

```bash
npm install
npm test                 # Run tests across workspaces
npx sst build            # SST build for infra
```

## Structure

Monorepo with 3 packages:

| Package | Role |
|---|---|
| `core` (`@web3-storage/content-claims`) | Claim types, client, UCAN server |
| `cli` | CLI for interacting with claims service |
| `infra` | AWS SST deployment (DynamoDB + S3) |

```
packages/core/
  src/capability/assert.js    # assert/* capability definitions (6 types)
  src/server/service/assert.js # Handlers for assert/* capabilities
  src/client/index.js         # Client for querying claims
```

## Claim Types

| Claim | What it asserts |
|---|---|
| `assert/location` | Content is at a specific URL (with byte range) |
| `assert/inclusion` | Content is included in an aggregate |
| `assert/index` | Content is indexed by a ShardedDAGIndex |
| `assert/partition` | Content is partitioned across shards |
| `assert/relation` | Relationship between content CIDs |
| `assert/equals` | Two CIDs refer to the same content |

## Key Patterns

- Claims are stored as UCAN delegations (CAR-encoded)
- Claims are indexed by content multihash in DynamoDB
- Claims are served via HTTP GET `/claims?multihash=...`
- The indexing-service (Go) also handles claim publishing via its UCAN server

## What Breaks If You Change Things Here

- Claim format changes affect: indexing-service, freeway, blob-fetcher, upload-service
- Client library (`@web3-storage/content-claims`) used by 9 repos
- DynamoDB schema changes require migration in infra package
