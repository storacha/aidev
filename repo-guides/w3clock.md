# w3clock

Cloudflare Worker implementing a Merkle clock for CRDT-based key-value storage (Pail).

## Quick Reference

```bash
npm install
npm test               # mocha --experimental-vm-modules
npm run build          # Build worker + module
```

## Structure

```
src/
  index.js             # CF Worker entry point
  worker/
    service.js         # UCAN service (clock/advance, clock/head)
    durable-clock.js   # Durable Object implementation
  server/
    index.js           # Custom ucanto server (pre-dates @ucanto/server patterns)
  capabilities.js      # Capability definitions
```

## UCAN Capabilities

| Capability | Status | Purpose |
|---|---|---|
| `clock/advance` | Active | Advance clock with new event |
| `clock/head` | Active | Get current clock head |
| `clock/follow` | Commented out | Follow another clock |
| `clock/unfollow` | Commented out | Unfollow a clock |
| `clock/following` | Commented out | List followed clocks |

## Key Patterns

- Uses Cloudflare Durable Objects for persistent clock state
- Events are Merkle-clock events (DAG-CBOR encoded with parent links)
- The clock enables CRDT merge semantics for Pail key-value stores
- Custom ucanto server implementation (older codebase, doesn't use standard patterns)

## What Breaks If You Change Things Here

- Self-contained service — minimal external blast radius
- Clock event format changes break existing Pail databases
- Durable Object state migration needed for schema changes
