<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Egress Tracking Flow: End-to-End Trace

> **TL;DR:** Freeway wraps response body in a byte-counting TransformStream. On stream completion, creates a `space/egress/record` UCAN invocation and queues it to Cloudflare Queue (non-blocking via `ctx.waitUntil`). Queue consumer executes against upload-api, which maps space -> customer via provisionsStorage and records bytes in usageStorage. `usage/report` aggregates per billing period for Stripe invoicing.

## Overview

```
GET /ipfs/<CID>  →  Freeway serves content
    │
    ├── 1. withEgressTracker wraps response body in byte-counting stream
    ├── 2. When stream completes: create space/egress/record invocation
    ├── 3. Queue invocation to EGRESS_QUEUE (Cloudflare Queue)
    │
    ├── 4. Queue consumer processes record
    │
    ├── 5. space/egress/record handler in upload-api
    │     ├── Look up consumer (space → customer)
    │     └── usageStorage.record(space, customer, resource, bytes, servedAt)
    │
    └── 6. usage/report aggregates for billing
```

## Step-by-Step Trace

### Step 1: Byte Counting in Freeway

| | |
|---|---|
| **File** | `freeway/src/middleware/withEgressTracker.js` |
| **Middleware position** | #21 in the stack (after authorization, before DAG traversal) |

The middleware wraps the response body in a `TransformStream` that counts bytes:

```js
const responseBody = response.body.pipeThrough(
  createByteCountStream(async (totalBytesServed) => {
    if (totalBytesServed > 0) {
      // Create and queue egress record (Step 2-3)
    }
  })
)
return new Response(responseBody, { status, headers })
```

The callback fires when the stream is fully consumed (all bytes sent to client).

### Step 2: Create Egress Record Invocation

| | |
|---|---|
| **File** | `freeway/src/middleware/withEgressTracker.js` |
| **Capability** | `space/egress/record` |

```js
const invocation = Space.egressRecord.invoke({
  issuer: ctx.gatewayIdentity,           // gateway's Ed25519 signer
  audience: DID.parse(env.UPLOAD_SERVICE_DID),
  with: SpaceDID.from(space),            // space that owns the content
  nb: {
    resource: ctx.dataCid,               // CID of the content served
    bytes: totalBytesServed,             // total bytes counted
    servedAt: new Date().getTime(),      // timestamp
  },
  proofs: ctx.delegationProofs,          // content-serve delegation proofs
})
```

### Step 3: Queue to Cloudflare Queue

| | |
|---|---|
| **File** | `freeway/src/middleware/withEgressTracker.js` |
| **Infra** | `env.EGRESS_QUEUE` (Cloudflare Queue) |

```js
const archive = await invocation.buildIPLDView()
const archiveResult = await archive.archive()
ctx.waitUntil(
  env.EGRESS_QUEUE.send(dagJSON.encode({
    messageId: delegation.cid,
    invocation: archiveResult.ok,
    timestamp: Date.now()
  }))
)
```

- `ctx.waitUntil` extends Cloudflare Worker lifetime for async queueing
- Message encoded as DAG-JSON with the serialized invocation
- Non-blocking — response is already streaming to client

### Step 4: Queue Consumer

| | |
|---|---|
| **Repo** | w3infra (Cloudflare Worker queue consumer) |
| **Infra** | Cloudflare Queue → Worker binding |

The queue consumer deserializes the invocation and executes it against the upload-api service. This decouples the gateway response latency from the billing record processing.

### Step 5: space/egress/record Handler

| | |
|---|---|
| **File** | `w3up/packages/upload-api/src/space/record.js` |
| **Capability** | `space/egress/record` |
| **Infra** | `provisionsStorage` (DynamoDB), `usageStorage` |

```js
const egressRecord = async ({ capability, invocation }, context) => {
  // 1. Look up the consumer (customer) for this space
  const consumer = await context.provisionsStorage.getConsumer(
    provider,           // invocation audience (upload service DID)
    capability.with     // space DID
  )

  // 2. Record the egress event
  await context.usageStorage.record(
    capability.with,              // space
    consumer.ok.customer,         // customer (for billing)
    capability.nb.resource,       // CID served
    capability.nb.bytes,          // bytes served
    new Date(capability.nb.servedAt),  // when
    invocation.cid                // link to invocation
  )
}
```

### Step 6: Usage Reporting

| | |
|---|---|
| **File** | `w3up/packages/upload-api/src/usage/report.js` |
| **Capability** | `usage/report` with `nb: { period: { from, to } }` |

```js
const report = async ({ capability }, context) => {
  const space = capability.with
  const period = { from, to }   // Unix timestamps

  // Get storage providers for this space
  const providers = await context.provisionsStorage.getStorageProviders(space)

  // Aggregate usage per provider for the period
  for (const provider of providers.ok) {
    const usage = await context.usageStorage.report(provider, space, period)
    reports.push([provider, usage.ok])
  }

  return { ok: Object.fromEntries(reports) }
}
```

Usage reports include both storage and egress data for billing.

### Step 7: Billing Integration

| | |
|---|---|
| **Repo** | w3infra |
| **Integration** | Stripe (via billing service) |

The billing service periodically queries `usage/report` for each customer's spaces and generates invoices. The `usageStorage` aggregates egress bytes per space per billing period.

## Rate Limiting

| | |
|---|---|
| **File** | `freeway/src/middleware/withRateLimit.js` |
| **Position** | Before authorization (Step 17 in middleware stack) |

Rate limiting is checked before content is served. If rate limit is exceeded, a 429 response is returned and no egress is tracked (since no bytes are served).

## Infrastructure Summary

| Component | Type | Purpose |
|-----------|------|---------|
| Byte counting stream | TransformStream | Count bytes flowing through response |
| EGRESS_QUEUE | Cloudflare Queue | Async delivery of egress records |
| Queue consumer | CF Worker | Deserialize and execute egress invocations |
| provisionsStorage | DynamoDB | Space → customer mapping |
| usageStorage | DynamoDB | Egress/storage records per space per period |
| Billing service | Stripe integration | Invoice generation from usage reports |

## Key Files

| Role | File |
|------|------|
| Egress tracking middleware | `freeway/src/middleware/withEgressTracker.js` |
| Egress client middleware | `freeway/src/middleware/withEgressClient.js` |
| Egress record handler | `w3up/packages/upload-api/src/space/record.js` |
| Usage report handler | `w3up/packages/upload-api/src/usage/report.js` |
| Space capability (egress) | `w3up/packages/capabilities/src/space.js` |
| Usage capability | `w3up/packages/capabilities/src/usage.js` |
| Rate limiting | `freeway/src/middleware/withRateLimit.js` |
