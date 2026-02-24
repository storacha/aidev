---
name: new-capability
description: Step-by-step guide for adding a new UCAN capability to the Storacha system
user_invocable: true
---

# Step-by-step guide: Add a new UCAN capability

Walk through adding a new UCAN capability to the Storacha system, following existing patterns exactly.

## Instructions

When the user invokes this command, guide them through these steps. Ask which service/repo the capability belongs to before starting.

### Step 1: Define the Capability (JS)

Read `aidev/memory/tech/ucanto-framework.md` for the canonical pattern, then:

**File:** `upload-service/packages/capabilities/src/<domain>.js` (or appropriate capabilities package)

```js
import { capability, Schema } from '@ucanto/validator'

export const myCapability = capability({
  can: 'domain/verb',              // Follow domain/verb naming
  with: Schema.did({ method: 'key' }),  // Resource (usually space DID)
  nb: Schema.struct({              // Caveats (capability-specific params)
    field1: Schema.link(),
    field2: Schema.integer().optional(),
  }),
  derives: (claimed, delegated) => {
    // Derivation rules: can claimed be derived from delegated?
    // Return ok({}) or error
  },
})
```

**Conventions:**
- Capability name: `domain/verb` (e.g., `blob/add`, `space/info`)
- Resource (`with`): Almost always `Schema.did({ method: 'key' })` for space-scoped capabilities
- Export from the domain module and re-export from `index.js`

### Step 2: Define the Capability (Go, if needed)

Read `aidev/memory/tech/go-ecosystem.md` for the Go pattern:

**File:** `go-libstoracha/capabilities/<domain>/<verb>.go`

```go
var MyCapability = validator.NewCapability(
    "domain/verb",
    schema.DIDString(),
    MyCaveatsReader,
    validator.DefaultDerives,
)
```

### Step 3: Wire the Handler (JS)

**File:** `upload-service/packages/upload-api/src/<domain>.js`

```js
import * as MyCap from '@storacha/capabilities/domain'
import * as Server from '@ucanto/server'

export const myHandler = Server.provideAdvanced({
  capability: MyCap.myCapability,
  handler: async ({ capability, context }) => {
    const { field1, field2 } = capability.nb
    // Business logic here
    return Server.ok({ result: value })
  },
})
```

Then register in the service composition:

**File:** `upload-service/packages/upload-api/src/lib.js`

```js
export const createService = (context) => ({
  // ... existing services ...
  domain: {
    verb: createMyHandler(context),
  },
})
```

### Step 4: Wire the Handler (Go, if needed)

```go
server.WithServiceMethod(
    "domain/verb",
    server.Provide(mycap.MyCapability, handleMyCapability),
)
```

### Step 5: Add Client Support

**File:** `upload-service/packages/upload-client/src/<domain>.js`

```js
export const myAction = async (conf, params) => {
  const invocation = MyCap.myCapability.invoke({
    issuer: conf.agent,
    audience: conf.servicePrincipal,
    with: conf.resource,
    nb: { field1: params.field1, field2: params.field2 },
    proofs: conf.proofs,
  })
  const receipt = await invocation.execute(conf.connection)
  if (!receipt.out.ok) throw new Error(receipt.out.error.message)
  return receipt.out.ok
}
```

### Step 6: Check Blast Radius

Run `/impact` on the capabilities package to understand what repos need updating.

Key questions:
- Does this capability need to work in both JS and Go? (Check go-libstoracha)
- Does it need a new spec in the `specs/` repo?
- Does it affect any existing flow traces? (Check `aidev/memory/flows/`)
- Does it need infrastructure (new DynamoDB table, queue, etc.)? (Check `aidev/memory/architecture/infrastructure-decisions.md`)

### Step 7: Test

Follow existing test patterns:
- JS: Mocha test suite with shared `test/helpers/` fixtures, ed25519 test signers
- Go: testify assertions with mockery mocks
- Integration: Test the full invocation→receipt chain, not just the handler

### Common Gotchas

- **Don't forget derives**: If caveats have numeric ranges or linked resources, the derivation function must validate the claimed capability can be derived from the delegated one.
- **Schema version**: If this is a breaking change to an existing capability, version it (e.g., `blob/get/0.1` pattern used for backward compatibility).
- **Effects**: If this capability triggers async work, use `.fork(fx)` and `.join(fx)` to chain effects. Read `aidev/memory/tech/ucanto-framework.md` for the effect pattern.
- **Namespace**: New capabilities go in `@storacha/capabilities` (not `@web3-storage/capabilities`).
