<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Cross-Cutting Patterns: Storacha Codebase Conventions

> **TL;DR:** All async ops return `Result<T,X>` (`{ ok }` or `{ error }`) -- never throw. Errors extend `Failure` with `.name` string matching. Effects use `fork()`/`join()` on `OkBuilder` for async task chains. JS tests use Mocha + object-map test suites with shared ed25519 fixtures; Go uses testify + mockery. Files: JS kebab-case, Go snake_case. Capabilities: `domain/verb` naming. Two package namespaces: `@storacha/*` (new) and `@web3-storage/*` (legacy).

> Concepts: Result types (P0), Failure classes (P0), effect system (P0), testing patterns (P0), naming conventions (P0)
> Applies across: all JS and Go repos

## Error Handling

### JS: Result<T, X> discriminated union

Every async operation returns `{ ok: T } | { error: X }` — never throws.

```js
import { ok, error } from '@ucanto/core/result'

// Creating results
return ok({ piece: pieceCID })
return error(new BlobSizeOutsideOfSupportedRange(size, maxSize))

// Checking results
const result = await blobsStorage.has(digest)
if (result.error) {
  return result  // propagate directly — types are compatible
}
// result.ok is narrowed to the success type
```

**Custom error classes** extend `Failure` from `@ucanto/core`:
```js
import { Failure } from '@ucanto/core'

export class BlobSizeOutsideOfSupportedRange extends Failure {
  get name() { return 'BlobSizeOutsideOfSupportedRange' }
  describe() { return `Blob size ${this.blobSize} exceeded limit: ${this.maxUploadSize}` }
  toJSON() { return { ...super.toJSON(), maxUploadSize: this.maxUploadSize, blobSize: this.blobSize } }
}
```

**Error matching** is by name string: `if (err.name === 'RecordKeyConflict') { ... }`

### Go: result.Result[O, X] generic interface

```go
import "github.com/storacha/go-ucanto/core/result"

// Creating results
return result.Ok[OkType, ErrType](value), nil
return result.Error[OkType, ErrType](failure), nil

// Pattern matching (Go doesn't have discriminated unions)
result.MatchResultR1(res,
    func(ok OkType) string { return "success" },
    func(err ErrType) string { return err.Error() },
)

// Wrapping (T, error) → Result
res := result.Wrap(someFunc())
```

**Failure interface** in Go:
```go
type Failure interface {
    error
    Name() string
}
```

### Server-level errors (ucanto)

Three system errors in `@ucanto/server`:
- `HandlerNotFound` — capability not routed to any handler
- `HandlerExecutionError` — unhandled exception inside handler
- `InvocationCapabilityError` — invocation had != 1 capability

## Effect System (fork/join)

Handlers return **transactions** — results with attached side effects:

```js
import * as Server from '@ucanto/server'

// In a handler:
return Server.ok({ site: { 'ucan/await': ['.out.ok.site', acceptance.link()] } })
  .fork(allocation.task)     // fire-and-forget: runs in parallel
  .fork(delivery.task)       // fire-and-forget
  .fork(acceptance.task)     // fire-and-forget
  .join(confirmation.cid)    // sequential: resolve after this completes

// The receipt carries: { out: Result, fx: { fork: [...], join?: ... } }
```

**`ucan/await` references** — a downstream task can reference output from an upstream receipt:
```js
url: { 'ucan/await': ['.out.ok.address.url', allocation.receipt.ran.link()] }
```

**Go equivalent:**
```go
return transaction.NewTransaction(result, transaction.WithEffects(
    fx.NewEffects(fx.WithFork(forkInvocation1, forkInvocation2)),
)), nil
```

## Async Patterns

### Queues (JS)
```js
// Queue interface: add() returns Result<Unit, QueueAddError>
await context.filecoinSubmitQueue.add({ piece, content, group })
```

### Cloudflare Workers background tasks
```js
ctx.waitUntil(env.EGRESS_QUEUE.send(dagJSON.encode({ ... })))
// Extends request lifetime for non-blocking side effects
```

### Job Queue (Go — Piri)
```go
type Service[T any] interface {
    Register(name string, fn func(context.Context, T) error, opts ...worker.JobOption[T]) error
    Enqueue(ctx context.Context, name string, msg T) error
    Start(ctx context.Context) error
    Stop(ctx context.Context) error
}
// DB-backed (SQLite/Postgres), supports dedup mode, configurable workers/retries
```

## Testing Patterns

### JS: Mocha + shared test suites

Tests are defined as **object maps** for reuse across implementations:
```js
// test/service.js — defines the suite
export const test = {
  'blob/add schedules allocation': async (assert, context) => {
    const result = await context.service.blob.add(...)
    assert.ok(result.ok)
  }
}

// test/test.js — runner that wraps object map into mocha describe/it
export const test = (suite) => {
  for (const [name, member] of Object.entries(suite)) {
    if (typeof member === 'function') {
      it(name, async () => {
        const context = await createContext()
        try { await member(assert, context) }
        finally { await cleanupContext(context) }
      })
    } else { describe(name, () => test(member)) }
  }
}
```

**Test context** assembles in-memory implementations of all storage/queue interfaces:
```js
const context = await createContext()
// context has: signer, connection, blobsStorage, allocationsStorage, ...
```

**Mocks** use `withCallParams` wrapper to track calls:
```js
const mock = mockService({ filecoin: { offer: withCallParams(handler) } })
// Later: mock.filecoin.offer.called, mock.filecoin.offer.callCount, mock.filecoin.offer._params
```

**Shared test fixtures** — same ed25519 keys across JS and Go:
```js
export const alice = ed25519.parse('MgCZT5vOnYZoVAeyjnzuJIVY9J4LNtJ+...')  // did:key:z6Mkk89bC3...
export const bob = ed25519.parse('MgCYbj5AJfVvdrjkjNCxB3iAUwx7RQHVQ...')    // did:key:z6MkffDZCk...
```

### Go: testify + mockery

```go
import "github.com/stretchr/testify/require"

func TestBlobAllocate(t *testing.T) {
    require.NoError(t, err)
    require.Equal(t, expected, actual)
}
```

**Auto-generated mocks** via mockery:
```go
mock := mocks.NewMockService(t)
mock.On("Method", args...).Return(result, nil)
// t.Cleanup auto-asserts expectations
```

**Shared fixtures** in `go-libstoracha/testutil/fixtures.go` — same keys as JS.

**Integration tests** (Piri) use testcontainers:
```go
func TestMain(m *testing.M) {
    internaltesting.SetupPostgresContainer(ctx)
    code := m.Run()
    internaltesting.TeardownPostgresContainer(ctx)
    os.Exit(code)
}
```

## Naming Conventions

### Capability naming
Pattern: `domain/verb` or `domain/subdomain/verb` with `*` wildcards for parent capabilities.
```
space/blob/add    blob/allocate    assert/location    ucan/attest
filecoin/offer    piece/accept     aggregate/offer    http/put
```

Go constant pattern: `const AddAbility = "space/blob/add"`

### File naming
| Language | Pattern | Example |
|----------|---------|---------|
| JS source | `kebab-case.js` | `blob-index.js`, `rate-limit.js` |
| JS middleware | `withCamelCase.js` | `withEgressTracker.js`, `withRateLimit.js` |
| JS types | paired `.types.ts` | `withEgressTracker.types.ts` |
| JS tests | `.spec.js` (primary) or `.test.js` | `blob-add.spec.js` |
| Go source | `snake_case.go` | `blob_index.go`, `rate_limit.go` |
| Go tests | `_test.go` | `blob_index_test.go` |

### Variable naming
| Language | Variables | Types/Classes | Constants | Exports |
|----------|-----------|---------------|-----------|---------|
| JS | `camelCase` | `PascalCase` | `SCREAMING_SNAKE` or `PascalCase` | named exports |
| Go | `camelCase` (unexported) | `PascalCase` (exported) | `PascalCase` | by case |

### Package namespaces

**JS — two eras (migration in progress):**
- New: `@storacha/*` (upload-service repo)
- Legacy: `@web3-storage/*` (w3up repo)
- Stable: `@ucanto/*` (ucanto repo, not migrating)
- Monorepo: `workspace:^` protocol in pnpm

**Go:**
- All under `github.com/storacha/*`
- Standard Go module imports (no workspace protocol)

### Handler registration mirrors capability paths

```js
// JS: 'space/blob/add' → service.space.blob.add
const service = {
  space: { blob: { add: blobAddProvider(context) } }
}

// Go: 'blob/allocate' → server.WithServiceMethod("blob/allocate", handler)
```

## Key Files Index

| Role | File |
|------|------|
| Result type (JS) | `ucanto/packages/interface/src/lib.ts` |
| Result helpers (JS) | `ucanto/packages/core/src/result.js` |
| Failure class (JS) | `ucanto/packages/core/src/result.js` |
| Server errors (JS) | `ucanto/packages/server/src/error.js` |
| Result type (Go) | `go-ucanto/core/result/result.go` |
| Failure interface (Go) | `go-ucanto/core/result/failure/faillure.go` |
| Transaction (JS) | `ucanto/packages/server/src/handler.js` |
| Transaction (Go) | `go-ucanto/server/transaction/transaction.go` |
| Test context (JS) | `w3up/packages/upload-api/test/helpers/context.js` |
| Test runner (JS) | `w3up/packages/upload-api/test/test.js` |
| Mock service (JS) | `w3up/packages/filecoin-api/test/context/mocks.js` |
| Test fixtures (JS) | `w3up/packages/upload-api/test/helpers/utils.js` |
| Test fixtures (Go) | `go-libstoracha/testutil/fixtures.go` |
| Test helpers (Go) | `go-libstoracha/testutil/helpers.go` |
| Job queue (Go) | `piri/lib/jobqueue/jobqueue.go` |

## Authoritative Specs
- [ucanto Result Type](https://github.com/storacha/ucanto/blob/main/packages/interface/src/lib.ts)
- [Storacha Conventions (CLAUDE.md)](../../../CLAUDE.md)
