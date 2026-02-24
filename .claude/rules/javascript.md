# JavaScript/TypeScript Conventions

## Imports
- Prefer `@storacha/*` packages over `@web3-storage/*` (legacy)
- ucanto imports: `@ucanto/core`, `@ucanto/server`, `@ucanto/client`, `@ucanto/validator`
- IPLD: `multiformats`, `@ipld/car`, `@ipld/dag-cbor`, `@ipld/dag-json`

## Patterns
- Service handlers: `Server.provideAdvanced({ capability, handler })`
- Return `Server.ok({})` or `Server.error(new SomeFailure())` — never throw
- Capability definition: `capability({ can, with, nb, derives })` from `@ucanto/validator`
- Effects: `.fork(fx)` / `.join(fx)` for async workflows

## Monorepo Awareness
- `upload-service` — newer, `@storacha/*` namespace (16 packages), prefer for active development
- `w3up` — older, `@web3-storage/*` namespace (10 packages)
- 8 packages exist in both; prefer `upload-service` versions

## Testing
- Framework: Mocha
- Pattern: shared test suites via `testVariant` helper
- Fixtures: ed25519 test signers from `@ucanto/principal/ed25519`
- Always test the full invocation->receipt chain, not just handler logic
