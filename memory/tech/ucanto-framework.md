<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# ucanto Framework: Patterns & Reference

> **TL;DR:** ucanto is the UCAN-based RPC framework powering all Storacha APIs. Every API call is a signed invocation carrying a delegation proof chain. Capabilities are defined with `capability()` + `Schema`, handled via `Server.provide()` or `Server.provideAdvanced()` (for effects), and composed into service objects mirroring the `domain/verb` namespace. Transport is CAR-encoded over HTTP. 7 packages: core, server, client, transport, principal, validator, interface.

> Concepts: ucanto RPC (P0), capability definition (P0), Server.provide (P0), service factories (P0), effect system (P0), connection model (P0), CAR transport (P0)
> Key repos: ucanto, w3up (capabilities, upload-api), w3infra, w3clock, freeway, content-claims, upload-service

## Architecture Overview

ucanto is Storacha's UCAN-based RPC framework. Every API call is a UCAN invocation with full delegation chain support. The architecture:

```
Client                          Server
  |                               |
  | capability.invoke({           |
  |   issuer, audience,           |
  |   with, nb, proofs            |
  | })                            |
  |                               |
  |-- CAR.outbound encode ------->|
  |   (invocation + proofs        |
  |    as DAG-CBOR blocks)        |
  |                               |--> CAR.inbound decode
  |                               |--> validate UCAN chain
  |                               |--> route to handler via service object
  |                               |--> execute handler
  |                               |--> return signed Receipt
  |<-- CAR response --------------|
  |                               |
  | receipt.out.ok / .out.error   |
```

**7 packages:** core, server, client, transport, principal, validator, interface

## Patterns

### Pattern: Define a capability
**When:** Adding a new UCAN capability to the system
**Template:**
```js
import { capability, Schema, ok, fail, and, equalWith, equal } from '@ucanto/validator'
import { SpaceDID } from './utils.js'  // Schema.did({ method: 'key' })

export const myCapability = capability({
  can: 'namespace/action',           // ability string
  with: SpaceDID,                    // resource URI constraint
  nb: Schema.struct({                // caveats schema
    content: Schema.link(),          // CID link
    size: Schema.integer().optional(),
  }),
  derives: (claimed, delegated) => { // attenuation check
    return (
      and(equalWith(claimed, delegated)) ||
      and(equal(claimed.nb.content, delegated.nb.content, 'content')) ||
      ok({})
    )
  },
})
```
**Variations:**
- `with: URI.match({ protocol: 'did:' })` — for service-scoped capabilities (content claims)
- `with: Schema.did()` — any DID (filecoin capabilities)
- `with: DID.match({ method: 'key' })` — specific DID method
- No `derives` — defaults to structural equality
- Complex derives: size constraints (`claim.nb.size > from.nb.size ? fail(...) : ok({})`), subset checks (`subsetCapabilities(...)`)
**Key files:** `w3up/packages/capabilities/src/blob.js`, `w3up/packages/capabilities/src/upload.js`, `w3up/packages/capabilities/src/store.js`, `w3up/packages/capabilities/src/access.js`, `content-claims/packages/core/src/capability/assert.js`
**Gotchas:**
- The `nb` (caveats) schema defines what the client sends as arguments — it's both the parameter definition AND the authorization constraint
- `derives` must return `ok({})` for valid attenuation or `fail("message")` for invalid — chain with `and()` which short-circuits on first error
- Always use `equalWith` for the resource check — capabilities with different `with` values CANNOT delegate to each other

### Pattern: Handle a capability (simple)
**When:** Implementing a handler for a capability — no side effects needed
**Template:**
```js
import * as Server from '@ucanto/server'
import * as MyCapability from '@web3-storage/capabilities/myThing'

export const myHandler = (context) =>
  Server.provide(MyCapability.add, async ({ capability, invocation }) => {
    const space = capability.with         // resource DID
    const { content, size } = capability.nb  // validated caveats
    const issuer = invocation.issuer.did()

    // Do work using context (DB access, storage, etc.)
    const result = await context.myTable.insert({ space, content })

    return result.error
      ? { error: { name: 'StoreError', message: result.error.message } }
      : { ok: { status: 'done' } }
  })
```
**Key files:** `w3up/packages/upload-api/src/upload/add.js`, `w3up/packages/upload-api/src/blob/allocate.js`
**Gotchas:**
- Return `{ ok: ... }` or `{ error: { name, message } }` — must be a Result union
- `capability.with` is the validated resource URI, `capability.nb` has validated caveats
- `invocation` gives access to `.issuer`, `.audience`, `.link()` (CID of invocation), `.blocks` (attached blocks)

### Pattern: Handle a capability with effects (provideAdvanced)
**When:** Handler needs to produce side effects (fork tasks, chain invocations)
**Template:**
```js
import * as Server from '@ucanto/server'

export const myAdvancedHandler = (context) =>
  Server.provideAdvanced({
    capability: MyCapability.add,
    handler: async ({ capability, invocation }) => {
      const allocation = await allocate(context, capability.nb)
      const delivery = await scheduleDelivery(context, capability.nb)
      const acceptance = await scheduleAcceptance(context, capability.nb)

      return Server.ok({ site: { 'ucan/await': ['.out.ok.site', acceptance.task.link()] } })
        .fork(allocation.task)     // enqueue allocation
        .fork(delivery.task)       // enqueue HTTP PUT
        .fork(acceptance.task)     // enqueue blob/accept
    },
  })
```
**Variations:**
- `.join(task)` — task that waits for all forks to complete (rare)
- `Server.error(...)` — return an error with effects
- Adding audience schema: `{ capability, audience: Schema.did({ method: 'web' }).or(Schema.did({ method: 'key' })), handler }`
**Key files:** `w3up/packages/upload-api/src/blob/add.js`, `freeway/src/server/service.js`
**Gotchas:**
- `Server.ok(value)` returns an `OkBuilder` — you MUST chain `.fork()` to add effects, not modify a separate effects object
- The `'ucan/await'` pattern in results means "this value will be resolved when the referenced task completes"
- Fork tasks are UCAN invocations — they get enqueued and executed asynchronously

### Pattern: Wire handlers into a service
**When:** Composing handlers into a routable service object
**Template:**
```js
// Sub-service factory (one per domain):
export function createBlobService(context) {
  return {
    add: blobAddProvider(context),
    list: blobListProvider(context),
    remove: blobRemoveProvider(context),
    get: { 0: { 1: blobGetProvider(context) } },  // versioned: blob/get/0/1
  }
}

// Top-level composition (mirrors capability namespace):
export const createService = (context) => ({
  access: createAccessService(context),
  space: createSpaceService(context),
  store: createStoreService(context),
  upload: createUploadService(context),
  ucan: createUcanService(context),
  filecoin: createFilecoinService(context).filecoin,
  usage: createUsageService(context),
  // ... more domains
})
```
**Key files:** `w3up/packages/upload-api/src/lib.js:176-194`, `w3up/packages/upload-api/src/blob.js`
**Gotchas:**
- Service object structure MUST mirror the capability namespace: `store/add` → `service.store.add`
- Versioned capabilities use nested objects: `blob/get/0/1` → `service.blob.get[0][1]`
- Context is the dependency injection mechanism — holds DB refs, signers, connections

### Pattern: Create a server
**When:** Setting up a ucanto RPC endpoint
**Template:**
```js
import * as Server from '@ucanto/server'
import * as CAR from '@ucanto/transport/car'
import { ed25519 } from '@ucanto/principal'

const server = Server.create({
  id: ed25519.parse(SERVICE_SECRET_KEY),  // server's signing identity
  codec: CAR.inbound,                      // decode CAR requests, encode CAR responses
  service: createService(context),         // handler tree
  catch: (error) => errorReporter.catch(error),
  validateAuthorization: (auth) => validateAuthorization(context, auth),
})
```
**Variations:**
- `validateAuthorization: () => ({ ok: {} })` — skip validation (tests, simple services like w3clock)
- `codec: Legacy.inbound` — for backwards compatibility (supports both legacy and modern encoding)
- Server doubles as a channel for local testing: `Client.connect({ channel: server })`
**Key files:** `w3up/packages/upload-api/src/lib.js:34-60`, `w3clock/src/server/index.js`

### Pattern: Connect a client to a service
**When:** Creating a connection to invoke capabilities remotely
**Template:**
```js
import { connect } from '@ucanto/client'
import { CAR, HTTP } from '@ucanto/transport'

const connection = connect({
  id: DID.parse('did:web:up.storacha.network'),  // service's public DID
  codec: CAR.outbound,                            // encode CAR requests
  channel: HTTP.open({
    url: new URL('https://up.storacha.network'),
    method: 'POST',
  }),
})
```
**Key files:** `w3infra/upload-api/config.js:46-60`, `w3clock/src/client/index.js:93-100`
**Gotchas:**
- Always `CAR.outbound` for client, `CAR.inbound` for server — they're asymmetric codecs
- `HTTP.open` creates a channel that sends POST requests with `application/vnd.ipld.car` content type
- Service DID is `did:web:up.storacha.network` in production

### Pattern: Invoke a capability
**When:** Client executing a capability on a remote service
**Template:**
```js
const receipt = await MyCapability.add
  .invoke({
    issuer: agentSigner,                  // client's Ed25519 key
    audience: connection.id,              // service DID
    with: spaceDID,                       // resource
    nb: { content: cid, size: 1024 },    // caveats/arguments
    proofs: [delegation],                 // proof chain
  })
  .execute(connection)

if (receipt.out.ok) {
  // success: receipt.out.ok contains the result
} else {
  // error: receipt.out.error has { name, message }
}
```
**Variations:**
- `invocation.attach(block)` — attach extra blocks (used in w3clock for event data)
- Batch: `connection.execute([inv1, inv2])` — multiple invocations in one request
**Key files:** `w3clock/src/client/index.js:20-35`

### Pattern: Generate and manage keys
**When:** Creating signing identities for agents/services
**Template:**
```js
import { ed25519 } from '@ucanto/principal'

// Generate new keypair
const agent = await ed25519.generate()

// Serialize for storage
const serialized = ed25519.format(agent)  // "Mg..." base64 string

// Restore from stored key
const restored = ed25519.parse(serialized)

// Get public DID
const did = agent.did()  // "did:key:z6Mk..."
```
**Key files:** `ucanto/packages/principal/`, `w3up/packages/access-client/src/space.js`

## Schema Quick Reference

```js
// Primitives
Schema.bytes()                    // Uint8Array
Schema.integer()                  // integer
Schema.string()                   // string
Schema.boolean()                  // boolean
Schema.number()                   // number

// Structures
Schema.struct({ key: type })      // object with named fields
Schema.array(type)                // array of type
Schema.dictionary({ value: type }) // map/dict
Schema.tuple([type1, type2])      // fixed-length tuple
Schema.variant({ tag: type })     // tagged union

// Links & DIDs
Schema.link()                     // any CID
Schema.link({ version: 1 })      // CIDv1 only
Schema.link({ code: 0x0202 })    // specific codec
Link.match({ code, version })    // CID link matcher
Schema.did()                      // any DID
Schema.did({ method: 'key' })    // specific method
DID.match({ method: 'mailto' })  // DID matcher
URI.match({ protocol: 'did:' })  // URI matcher
Schema.principal()                // DID principal

// Modifiers
type.optional()                   // field may be absent
type.or(otherType)                // union
type.greaterThan(n)               // numeric constraint
```

## Key Files Index

| Role | File |
|------|------|
| capability() + Schema + derives | `ucanto/packages/validator/src/` |
| Server.provide / provideAdvanced | `ucanto/packages/server/src/handler.js` |
| Effect system (ok/error/fork/join) | `ucanto/packages/server/src/handler.js:101-267` |
| Server.create | `ucanto/packages/server/src/server.js` |
| Client.connect / invoke | `ucanto/packages/client/src/` |
| CAR transport | `ucanto/packages/transport/` |
| ed25519 principal | `ucanto/packages/principal/` |
| Blob capabilities | `w3up/packages/capabilities/src/blob.js` |
| Upload capabilities | `w3up/packages/capabilities/src/upload.js` |
| Store capabilities | `w3up/packages/capabilities/src/store.js` |
| Access capabilities | `w3up/packages/capabilities/src/access.js` |
| Space capabilities | `w3up/packages/capabilities/src/space.js` |
| Filecoin capabilities | `w3up/packages/capabilities/src/filecoin/` |
| UCAN meta capabilities | `w3up/packages/capabilities/src/ucan.js` |
| Content claims capabilities | `content-claims/packages/core/src/capability/assert.js` |
| PDP capabilities (newer) | `upload-service/packages/capabilities/src/pdp.js` |
| Service composition | `w3up/packages/upload-api/src/lib.js:176-194` |
| blob/add handler (effects) | `w3up/packages/upload-api/src/blob/add.js` |
| upload/add handler (simple) | `w3up/packages/upload-api/src/upload/add.js` |
| index/add handler | `w3up/packages/upload-api/src/index/add.js` |
| Production connection | `w3infra/upload-api/config.js:46-60` |
| Server test | `ucanto/packages/server/test/server.spec.js` |

## Capability Catalog (by domain)

Complete registry of all 102 unique capabilities across 82 repos. Sourced from scanner data (api-surface-map.json). Capabilities are defined primarily in `upload-service/packages/capabilities/` (authoritative) with some also in `w3up/packages/capabilities/` (legacy mirror), `content-claims`, `w3clock`, and `freeway`.

### Core Storage & Upload

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Storage (parent) | `space/blob/*`, `blob/*` | `capabilities/src/blob.js` |
| Storage | `space/blob/add`, `space/blob/remove`, `space/blob/list`, `space/blob/get/0/1`, `space/blob/replicate` | `capabilities/src/blob.js` |
| Upload (parent) | `upload/*` | `capabilities/src/upload.js` |
| Upload | `upload/add`, `upload/remove`, `upload/list`, `upload/get` | `capabilities/src/upload.js` |
| Index (parent) | `space/index/*` | `capabilities/src/index.js` |
| Index | `space/index/add` | `capabilities/src/index.js` |
| Legacy Store (parent) | `store/*` | `capabilities/src/store.js` |
| Legacy Store | `store/add`, `store/remove`, `store/list`, `store/get` | `capabilities/src/store.js` |

### Service-Internal (blob lifecycle)

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| W3S Blob (parent) | `web3.storage/blob/*` | `capabilities/src/web3.storage.js` |
| W3S Blob | `web3.storage/blob/allocate`, `web3.storage/blob/accept` | `capabilities/src/web3.storage.js` |
| Blob (service-level parent) | `blob/*` | `capabilities/src/blob.js` |
| Blob (service-level) | `blob/allocate`, `blob/accept` | `capabilities/src/blob.js` |
| Blob Replica (parent) | `blob/replica/*` | `capabilities/src/blob.js` |
| Blob Replica | `blob/replica/allocate`, `blob/replica/transfer` | `capabilities/src/blob.js` |
| HTTP | `http/put` | `capabilities/src/http.js` |

### Access & Identity

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Access (parent) | `access/*` | `capabilities/src/access.js` |
| Access | `access/authorize`, `access/confirm`, `access/claim`, `access/delegate` | `capabilities/src/access.js` |
| Space (parent) | `space/*` | `capabilities/src/space.js` |
| Space | `space/info` (implied), `space/allocate` | `capabilities/src/space.js` |

### Content Serving & Retrieval

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Content Serve (parent) | `space/content/serve/*`, `space/content/*` | `capabilities/src/space.js` |
| Content Serve | `space/content/serve/transport/http`, `space/content/serve/egress/record` | `freeway/src/capabilities/serve.js` |
| Content Retrieve | `space/content/retrieve` | `capabilities/src/space.js` |
| Content Decrypt | `space/content/decrypt` | `capabilities/src/space.js` |

### Encryption (UCAN KMS)

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Encryption | `space/encryption/setup`, `space/encryption/key/decrypt` | `capabilities/src/space.js` |

### Filecoin Pipeline

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Filecoin (parent) | `filecoin/*` | `capabilities/src/filecoin/` |
| Filecoin Storefront | `filecoin/offer`, `filecoin/submit`, `filecoin/accept`, `filecoin/info` | `capabilities/src/filecoin/storefront.js` |
| Aggregator | `aggregate/offer`, `aggregate/accept` | `capabilities/src/filecoin/aggregator.js` |
| Piece | `piece/offer`, `piece/accept` | `capabilities/src/filecoin/piece.js` |
| Deal Tracker | `deal/info` | `capabilities/src/filecoin/deal-tracker.js` |
| PDP (newer) | `pdp/accept`, `pdp/info` | `upload-service/.../pdp.js` |

### Content Claims & Indexing

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Assert (parent) | `assert/*` | `capabilities/src/assert.js` and `content-claims/.../assert.js` |
| Assert | `assert/location`, `assert/inclusion`, `assert/index`, `assert/partition`, `assert/relation`, `assert/equals` | both repos |
| Claim (parent) | `claim/*` | `capabilities/src/claim.js` |
| Claim | `claim/cache` | `capabilities/src/claim.js` |

### Clock (Merkle CRDT)

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Clock (parent) | `clock/*` | `w3clock` |
| Clock | `clock/advance`, `clock/head`, `clock/follow`, `clock/unfollow`, `clock/following` | `w3clock` |

### Plan, Billing & Usage

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Plan | `plan/get`, `plan/set`, `plan/create-admin-session`, `plan/create-checkout-session` | `capabilities/src/plan.js` |
| Usage (parent) | `usage/*` | `capabilities/src/usage.js` |
| Usage | `usage/report` | `capabilities/src/usage.js` |
| Account Egress (parent) | `account/egress/*` | `capabilities/src/space.js` |
| Account Egress | `account/egress/get` | `capabilities/src/space.js` |
| Account Usage (parent) | `account/usage/*` | `capabilities/src/space.js` |
| Account Usage | `account/usage/get` | `capabilities/src/space.js` |
| Subscription | `subscription/get`, `subscription/list` | `capabilities/src/subscription.js` |
| Customer | `customer/get` | `capabilities/src/customer.js` |
| Consumer | `consumer/get`, `consumer/has` | `capabilities/src/consumer.js` |
| Provider | `provider/add` | `capabilities/src/provider.js` |

### Admin & Rate Limiting

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Admin (parent) | `admin/*` | `capabilities/src/admin.js` |
| Rate Limit | `rate-limit/add`, `rate-limit/list`, `rate-limit/remove` | `capabilities/src/rate-limit.js` |

### UCAN Meta & System

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Top | `*` (root capability) | `capabilities/src/top.js` |
| UCAN (parent) | `ucan/*` | `capabilities/src/ucan.js` |
| UCAN | `ucan/attest`, `ucan/revoke`, `ucan/conclude` | `capabilities/src/ucan.js` |
| Console | `console/*`, `console/log`, `console/error` | `capabilities/src/console.js` |

### Ucanto Examples (not production)

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Account | `account/verify` | `ucanto/packages/interface/src/capability.ts` |
| File | `file/read`, `file/write` | `ucanto/packages/interface/src/capability.ts` |

### External / App-Specific

| Domain | Capabilities | Key File |
|--------|-------------|----------|
| Bluesky Backup | `bskybackups.storacha.network/atproto` | `bluesky-backup-webapp-server/src/lib/capabilities.ts` |

## Design Rationale

ucanto exists because standard REST/gRPC cannot express delegated authorization natively. By making every API call a signed UCAN invocation:
- **Authorization is first-class**: Every request carries a proof chain from the resource owner to the invoker
- **Delegation is composable**: Users can grant fine-grained access without touching the server
- **Receipts are verifiable**: Results are signed and content-addressed, enabling async pipelines (fork/join effects)
- **Transport is flexible**: CAR-encoded requests carry the invocation + all referenced delegations in one payload
- **Type safety**: The Schema system validates caveats at both compile time (TypeScript) and runtime (invocation validation)

## Authoritative Specs
- [UCAN Spec (v1.0 RC)](https://github.com/ucan-wg/spec)
- [UCAN Invocation Spec](https://github.com/ucan-wg/invocation)
- [ucanto Source (JS)](https://github.com/storacha/ucanto)
- [go-ucanto Source (Go)](https://github.com/storacha/go-ucanto)
