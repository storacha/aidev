# ucanto

UCAN-based RPC framework. The foundation for all Storacha service communication. 7 packages.

## Quick Reference

```bash
pnpm install
pnpm test              # Run all tests across packages
pnpm build             # tsc across all packages
```

## Packages

| Package | Role |
|---|---|
| `interface` | TypeScript type definitions for all ucanto abstractions |
| `core` | Invocation/delegation/receipt types, IPLD encoding, block model |
| `client` | Client-side invocation builder, connection, `invoke()` |
| `server` | Server-side handler routing, `provide()`, `provideAdvanced()` |
| `transport` | CAR-encoded HTTP transport, legacy codec, header-car |
| `principal` | Ed25519/RSA signers and verifiers, DID parsing |
| `validator` | Proof chain validation, authorization, `ucan/attest` |

## Key Patterns

- **Capability definition**: `capability({ can: 'domain/verb', with: Schema.did(), nb: Schema.struct({...}) })`
- **Server handler**: `Server.provide(Capability, async (input) => ({ ok: result }))` for simple, `Server.provideAdvanced({capability, handler})` for effects
- **Effect system**: `Server.ok(value).fork(effect1).join(effect2)` creates fork/join execution graph
- **Connection**: `Client.connect({ id: serviceDID, channel: HTTP.open({url}), codec: CAR.outbound })`
- **Transport**: Invocations encoded as CAR, sent via HTTP POST, responses as CAR with receipts

## What Breaks If You Change Things Here

**EXTREME blast radius** — 20+ repos depend on ucanto packages.

- `interface` changes: every repo using TypeScript types needs updating
- `core` changes: affects all invocation/delegation encoding
- `server` changes: affects all service implementations
- `transport` changes: affects all client-server communication
- Wire format changes are essentially impossible without coordinated migration

## Key Files

| File | What it does |
|---|---|
| `packages/server/src/server.js` | Server.create(), invoke(), provide() |
| `packages/server/src/handler.js` | Handler execution and receipt creation |
| `packages/core/src/invocation.js` | Invocation construction and encoding |
| `packages/core/src/delegation.js` | Delegation (UCAN token) model |
| `packages/core/src/receipt.js` | Receipt model with effects |
| `packages/validator/src/lib.js` | Authorization validation, ucan/attest |
| `packages/client/src/connection.js` | Client connection to service |
