# upload-service

Primary monorepo for Storacha's upload/storage service. `@storacha/*` namespace (newer, preferred over w3up).

## Quick Reference

```bash
pnpm install           # Install dependencies
pnpm test              # Run all tests
pnpm -r run test       # Run tests across workspaces
pnpm build             # Build all packages (nx)
```

## Structure

16 packages in `packages/`:

| Package | Role |
|---|---|
| `capabilities` | All UCAN capability definitions (`@storacha/capabilities`) |
| `upload-api` | Server-side handlers for blob/upload/index/filecoin/access/ucan |
| `upload-client` | Client upload orchestration (shard, blob/add, index/add, upload/add) |
| `w3up-client` | High-level client SDK (`@storacha/client`) |
| `access-client` | Agent/space management, login flow (`@storacha/access`) |
| `filecoin-api` | Filecoin pipeline (storefront/aggregator/dealer/deal-tracker) |
| `filecoin-client` | Client for filecoin/offer invocations |
| `blob-index` | ShardedDAGIndex encode/decode |
| `did-mailto` | did:mailto DID method |
| `cli` | CLI tool (`@storacha/cli`) |
| `encrypt-upload-client` | Client-side encryption before upload |
| `ucn` | UCN (Storacha network) server |
| `router` | Request routing |
| `principal-resolver` | DID resolution |
| `console` | Console output capabilities |
| `eslint-config-w3up` | Shared ESLint config |

## Key Patterns

- **Service composition**: `packages/upload-api/src/lib.js` → `createService()` wires all handlers
- **Handler pattern**: `Server.provide(Capability, handler)` or `Server.provideAdvanced({capability, handler})`
- **Effect system**: `blob/add` uses `fork()`/`join()` for allocate → put → accept orchestration
- **Test pattern**: Mocha + shared test suites exported as object maps, run via `testVariant`
- **Versioning**: Nx Release with version plans (see CONTRIBUTING.md)

## What Breaks If You Change Things Here

- `capabilities` package: affects 11+ external repos (see shared-packages.md)
- `upload-api` handlers: affects w3infra (deploys these handlers), w3filecoin-infra
- `upload-client`: affects freeway, w3infra, admin
- `filecoin-api`: affects w3filecoin-infra

## Key Files

| File | What it does |
|---|---|
| `packages/upload-api/src/lib.js` | Service composition — all handlers wired here |
| `packages/upload-api/src/blob/add.js` | blob/add orchestration (allocate → put → accept) |
| `packages/upload-api/src/blob/allocate.js` | Presigned URL generation for upload |
| `packages/upload-api/src/blob/accept.js` | Confirms blob stored, publishes location claim |
| `packages/upload-api/src/index/add.js` | Index registration (IPNI publish + index claim) |
| `packages/capabilities/src/blob.js` | blob/* capability definitions |
| `packages/capabilities/src/space.js` | space/* capability definitions |
| `packages/upload-client/src/index.js` | Client upload pipeline entry |
| `packages/upload-client/src/sharding.js` | ShardingStream (~127MB shards) |
