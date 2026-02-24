# Storacha Conventions

## Naming
- Capabilities: `domain/verb` (e.g., `blob/add`, `space/info`)
- JS files: kebab-case
- Go files: snake_case
- Imports: `@storacha/*` (new), `@web3-storage/*` (legacy), `@ucanto/*` (stable)
- Go imports: `github.com/storacha/*`

## Error Handling
- JS: `Result<T,X>` discriminated union (`{ ok }` or `{ error }`). Never throw from service handlers.
- `Failure` base class with `.name` string matching for error types
- Go: `result.Result[O,X]` from go-ucanto

## Effects
- Use `fork()`/`join()` on `OkBuilder` for async workflows
- `ucan/await` references receipts from prior invocations

## Testing
- JS: Mocha + shared test suites passed to `testVariant`
- Go: testify assertions + mockery mocks
- Use shared ed25519 fixtures for deterministic DIDs in tests
