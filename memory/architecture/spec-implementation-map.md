<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Spec-to-Implementation Map

> **TL;DR:** 24 specs covering 47 capabilities; 41 are fully implemented, 6 are missing/partial. Most specs are FULL status. Key gaps: `w3-provider` (3 of 4 missing), `w3-account` (capability-only, no handlers in upload-api), `w3-replication` (partial, newer feature). Notable divergences: `blob/allocate` uses `web3.storage/` prefix in code, two parallel egress models (JS vs Go), encryption capabilities have no spec document.

## Legend

- **FULL**: All spec capabilities have handlers in code
- **PARTIAL**: Some capabilities implemented, some missing
- **SPEC-ONLY**: Spec exists but no/minimal implementation
- **IMPL-ONLY**: Implementation exists with no spec coverage

---

## Per-Spec Status

### 1. w3-blob.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `space/blob/add` | Implemented | `w3up/packages/upload-api/src/blob/add.js` |
| `blob/allocate` (as `web3.storage/blob/allocate`) | Implemented | `w3up/packages/upload-api/src/blob/allocate.js` + Piri (Go) |
| `http/put` | Implemented | Client-side execution, orchestrated by `blob/add.js` |
| `blob/accept` (as `web3.storage/blob/accept`) | Implemented | `w3up/packages/upload-api/src/blob/accept.js` + Piri (Go) |
| `assert/location` | Implemented | Published by `blob/accept` handler |
| `space/blob/list` | Implemented | `w3up/packages/upload-api/src/blob/list.js` |
| `space/blob/remove` | Implemented | `w3up/packages/upload-api/src/blob/remove.js` |
| `space/blob/get/0/1` | Implemented | `w3up/packages/upload-api/src/blob/get.js` |

**Divergences:**
- Spec says `blob/allocate` and `blob/accept`; code uses `web3.storage/blob/allocate` and `web3.storage/blob/accept` (provider-scoped namespace)
- Piri (Go) also implements `blob/allocate` and `blob/accept` as storage node handlers

### 2. w3-store.md — FULL (Legacy + Current)

| Capability | Status | Handler Location |
|---|---|---|
| `store/add` | Implemented | `w3up/packages/upload-api/src/store/add.js` |
| `store/get` | Implemented | `w3up/packages/upload-api/src/store/get.js` |
| `store/list` | Implemented | `w3up/packages/upload-api/src/store/list.js` |
| `store/remove` | Implemented | `w3up/packages/upload-api/src/store/remove.js` |
| `upload/add` | Implemented | `w3up/packages/upload-api/src/upload/add.js` |
| `upload/get` | Implemented | `w3up/packages/upload-api/src/upload/get.js` |
| `upload/list` | Implemented | `w3up/packages/upload-api/src/upload/list.js` |
| `upload/remove` | Implemented | `w3up/packages/upload-api/src/upload/remove.js` |

**Note:** `store/*` is the legacy protocol (pre-blob). The `blob/*` protocol (w3-blob.md) is the current approach. Both are live in the upload-api service.

### 3. w3-index.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `space/index/add` | Implemented | `w3up/packages/upload-api/src/index/add.js` |

### 4. w3-filecoin.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `filecoin/offer` | Implemented | `w3up/packages/filecoin-api/src/storefront/service.js` |
| `filecoin/submit` | Implemented | `w3up/packages/filecoin-api/src/storefront/service.js` |
| `filecoin/accept` | Implemented | `w3up/packages/filecoin-api/src/storefront/service.js` |
| `filecoin/info` | Implemented | `w3up/packages/filecoin-api/src/storefront/service.js` |
| `piece/offer` | Implemented | `w3up/packages/filecoin-api/src/aggregator/service.js` |
| `piece/accept` | Implemented | `w3up/packages/filecoin-api/src/aggregator/service.js` |
| `aggregate/offer` | Implemented | `w3up/packages/filecoin-api/src/dealer/service.js` |
| `aggregate/accept` | Implemented | `w3up/packages/filecoin-api/src/dealer/service.js` |
| `deal/info` | Implemented | `w3up/packages/filecoin-api/src/deal-tracker/service.js` |

**Extensions beyond spec:**
- `pdp/accept`, `pdp/info` — Go PDP pipeline in Piri (Ethereum-based proof system, separate from Spade deals)

### 5. w3-access.md — PARTIAL

| Capability | Status | Handler Location |
|---|---|---|
| `access/authorize` | Implemented | `w3up/packages/upload-api/src/access/authorize.js` |
| `access/delegate` | Implemented | `w3up/packages/upload-api/src/access/delegate.js` + `freeway/src/server/service.js` |
| `access/claim` | Implemented | `w3up/packages/upload-api/src/access/claim.js` |
| `access/request` | NOT implemented | Spec marks as deprecated, replaced by `access/authorize` |

**Extensions beyond spec:**
- `access/confirm` — Handles email confirmation link, creates session proofs (not in spec)

### 6. w3-ucan.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `ucan/attest` | Implemented | Defined in `ucanto/packages/validator/src/lib.js`, used in session proofs |
| `ucan/revoke` | Implemented | `w3up/packages/upload-api/src/ucan/revoke.js` |
| `ucan/conclude` | Implemented | `w3up/packages/upload-api/src/ucan/conclude.js` |

### 7. w3-space.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `space/info` | Implemented | `w3up/packages/upload-api/src/space/info.js` |

### 8. w3-plan.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `plan/get` | Implemented | `w3up/packages/upload-api/src/plan/get.js` |
| `plan/set` | Implemented | `w3up/packages/upload-api/src/plan/set.js` |

**Extensions beyond spec:**
- `plan/create-admin-session` — Creates Stripe admin session for billing management

### 9. w3-rate-limit.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `rate-limit/add` | Implemented | `w3up/packages/upload-api/src/rate-limit/add.js` |
| `rate-limit/list` | Implemented | `w3up/packages/upload-api/src/rate-limit/list.js` |
| `rate-limit/remove` | Implemented | `w3up/packages/upload-api/src/rate-limit/remove.js` |

### 10. w3-admin.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `consumer/get` | Implemented | `w3up/packages/upload-api/src/consumer/get.js` |
| `customer/get` | Implemented | `w3up/packages/upload-api/src/customer/get.js` |
| `subscription/get` | Implemented | `w3up/packages/upload-api/src/subscription/get.js` |
| `admin/upload/inspect` | Implemented | `w3up/packages/upload-api/src/admin/upload/inspect.js` |
| `admin/store/inspect` | Implemented | `w3up/packages/upload-api/src/admin/store/inspect.js` |

**Extensions beyond spec:**
- `subscription/list` — Lists all subscriptions for a customer
- `consumer/has` — Checks if consumer exists

### 11. w3-provider.md — PARTIAL

| Capability | Status | Handler Location |
|---|---|---|
| `provider/add` | Implemented | `w3up/packages/upload-api/src/provider-add.js` |
| `provider/get` | NOT implemented | Capability not defined in code |
| `consumer/add` | NOT implemented | Only `consumer/has` and `consumer/get` exist |
| `provider/publish` | NOT implemented | Capability not defined in code |

### 12. w3-account.md — PARTIAL

| Capability | Status | Handler Location |
|---|---|---|
| `account/usage/get` | Capability only | Defined in `upload-service/packages/capabilities/src/account/usage.js`, no handler in w3up |
| `account/egress/get` | Capability only | Defined in `upload-service/packages/capabilities/src/account/egress.js`, no handler in w3up |

**Note:** These capabilities may be handled by a separate billing/account service (w3infra). The capability definitions exist but handlers are not in the main upload-api service tree.

### 13. w3-clock.md — FULL (for specified capabilities)

| Capability | Status | Handler Location |
|---|---|---|
| `clock/advance` | Implemented | `w3clock/src/worker/service.js` |
| `clock/head` | Implemented | `w3clock/src/worker/service.js` |

**Note:** `clock/follow`, `clock/unfollow`, `clock/following` are defined as capabilities but **commented out** in the service. The spec only defines `advance` and `head`.

### 14. w3-egress-tracking.md — FULL (Go)

| Capability | Status | Handler Location |
|---|---|---|
| `space/egress/track` | Implemented | `etracker/` (Go service) |
| `space/egress/consolidate` | Implemented | `etracker/internal/consolidator/consolidator.go` |

**Note:** The JS upload-api uses a different egress tracking approach: `space/content/serve/egress/record` (capability in w3up) queued via Cloudflare Queue in Freeway. The etracker Go service implements the spec's model for Piri-based storage nodes.

### 15. w3-retrieval.md — FULL (Go)

| Capability | Status | Handler Location |
|---|---|---|
| `space/content/retrieve` | Implemented | `piri/pkg/fx/retrieval/` (Go) |

**Note:** Not implemented in JS. The `space/content/retrieve` capability is defined in `go-libstoracha/capabilities/space/content/retrieve.go` and handled by Piri's retrieval service.

### 16. w3-replication.md — PARTIAL

| Capability | Status | Handler Location |
|---|---|---|
| `space/blob/replicate` | Capability only | Defined in `upload-service/packages/capabilities`, handler in `upload-service/packages/upload-api/src/blob/replicate.js` |
| `blob/replica/allocate` | Implemented | Capability + Piri handler (Go) |
| `blob/replica/transfer` | Capability only | Defined in `upload-service/packages/capabilities`, Go handler in Piri |

**Note:** Replication is a newer feature. The JS side orchestrates (`space/blob/replicate`), and Piri handles the storage-node side (`blob/replica/allocate`).

### 17. w3-session.md — FULL (via other specs)

Defines the session model using `access/authorize` + `ucan/attest`. Both are implemented (see w3-access and w3-ucan).

### 18. content-serve-auth.md — FULL

| Capability | Status | Handler Location |
|---|---|---|
| `space/content/serve/*` | Implemented | Capability hierarchy in `w3up/packages/capabilities/src/space.js` |
| `space/content/serve/transport/http` | Implemented | `freeway/src/capabilities/serve.js` |
| `access/delegate` (for content-serve) | Implemented | `freeway/src/server/service.js` stores delegations |

### 19. w3-revocations-check.md — FULL

HTTP endpoint for checking delegation revocation status. Implementation: `w3up/packages/upload-api/src/utils/revocation.js`. Checked on every invocation via `validateAuthorization()`.

### 20. w3-store-ipfs-pinning.md — N/A (Mapping spec)

Maps IPFS Pinning Service API operations to existing `store/*` capabilities. No new capabilities to implement.

### 21. did-mailto.md — FULL

DID method specification. Implementation: `w3up/packages/did-mailto/src/index.js`. Fully implemented including `fromEmail()`, `toEmail()`, parsing, and validation.

### 22. http-header-ucan-invocation.md — N/A (Transport spec)

Defines how to send UCAN invocations via HTTP headers. Implemented in ucanto transport layer.

### 23. w3-ucan-bridge.md — N/A (Bridge spec)

HTTP bridge for executing UCAN invocations. No new capabilities defined.

### 24. Readme.md — N/A (Overview)

Index document listing all specs.

---

## Summary Table

| Spec | Status | Spec Caps | Implemented | Missing |
|---|---|---|---|---|
| w3-blob | FULL | 8 | 8 | 0 |
| w3-store | FULL | 8 | 8 | 0 |
| w3-index | FULL | 1 | 1 | 0 |
| w3-filecoin | FULL | 9 | 9 | 0 |
| w3-access | PARTIAL | 4 | 3 | 1 (access/request, deprecated) |
| w3-ucan | FULL | 3 | 3 | 0 |
| w3-space | FULL | 1 | 1 | 0 |
| w3-plan | FULL | 2 | 2 | 0 |
| w3-rate-limit | FULL | 3 | 3 | 0 |
| w3-admin | FULL | 5 | 5 | 0 |
| w3-provider | PARTIAL | 4 | 1 | 3 |
| w3-account | PARTIAL | 2 | 0 | 2 (capability-only) |
| w3-clock | FULL | 2 | 2 | 0 |
| w3-egress-tracking | FULL | 2 | 2 | 0 |
| w3-retrieval | FULL | 1 | 1 | 0 |
| w3-replication | PARTIAL | 3 | 1 | 2 (partial) |
| w3-session | FULL | — | — | — (references other specs) |
| content-serve-auth | FULL | 2 | 2 | 0 |
| w3-revocations-check | FULL | — | — | — (HTTP endpoint) |
| w3-store-ipfs-pinning | N/A | — | — | — (mapping spec) |
| did-mailto | FULL | — | — | — (DID method) |
| http-header-ucan-invocation | N/A | — | — | — (transport) |
| w3-ucan-bridge | N/A | — | — | — (bridge) |

**Overall: 47 spec-defined capabilities, 41 implemented, 6 missing/partial**

---

## Capabilities in Code with No Spec

These exist as implementations but aren't covered by any of the 24 specs:

| Capability | Where | Purpose |
|---|---|---|
| `access/confirm` | upload-api | Handles email confirmation, creates session proofs |
| `console/log`, `console/error` | upload-api | Debug/testing capabilities |
| `space/allocate` | upload-api | Rate limit + provisioning check before space operations |
| `space/encryption/setup` | ucan-kms | Initialize encryption for a space (KEK/DEK setup) |
| `space/encryption/key/decrypt` | ucan-kms | Decrypt a DEK using space's KEK |
| `space/content/decrypt` | upload-service | (Capability defined, handler unclear) |
| `space/content/serve/egress/record` | upload-api | JS egress tracking (Freeway queue path) |
| `pdp/accept`, `pdp/info` | Piri (Go) | PDP proof system (Ethereum-based) |
| `claim/cache` | indexing-service (Go) | Cache content claims from storage nodes |
| `plan/create-admin-session` | upload-api | Stripe billing admin session |
| `subscription/list` | upload-api | List subscriptions for a customer |
| `consumer/has` | upload-api | Check consumer existence |
| `access/grant` | Piri (Go) | Grant retrieval access (delegation creation) |
| `blob/retrieve` | go-libstoracha | Low-level blob retrieval capability |
| `assert/*` claims | content-claims, upload-service | Content claim system (6 types) |
| `usage/report` | upload-api | Aggregate usage for billing |

---

## Key Divergences: Spec vs Reality

1. **Namespace prefixing**: Spec says `blob/allocate`; code uses `web3.storage/blob/allocate` (provider-scoped)
2. **store/* vs blob/***: Both protocols live side-by-side. `store/*` is legacy; `blob/*` is current. Spec covers both.
3. **Two egress models**: Spec (w3-egress-tracking) describes `space/egress/track` model for storage nodes. JS gateway uses `space/content/serve/egress/record` via Cloudflare Queue. Both are live.
4. **Two Filecoin pipelines**: Spec describes JS pipeline. Go pipeline (PDP) uses different capabilities (`pdp/accept`, `pdp/info`).
5. **provider/get, consumer/add, provider/publish**: Defined in spec (w3-provider) but not implemented. Only `provider/add` is live.
6. **account/* capabilities**: Capability definitions exist in upload-service but handlers may be in a separate billing service (not in w3up upload-api).
7. **Encryption capabilities**: Fully implemented in ucan-kms but have no spec document.
8. **access/confirm**: Critical to the login flow but not specified. It's the server-side handler for email confirmation.
9. **Replication**: Newer feature, partially implemented. JS orchestration + Go storage-node handlers.

---

## Implementing Repos per Spec

| Spec | Primary Repo(s) |
|---|---|
| w3-blob | w3up (upload-api), Piri (Go) |
| w3-store | w3up (upload-api) |
| w3-index | w3up (upload-api), indexing-service (Go) |
| w3-filecoin | w3up (filecoin-api) |
| w3-access | w3up (upload-api), freeway |
| w3-ucan | w3up (upload-api), ucanto |
| w3-space | w3up (upload-api) |
| w3-plan | w3up (upload-api) |
| w3-rate-limit | w3up (upload-api) |
| w3-admin | w3up (upload-api) |
| w3-provider | w3up (upload-api) |
| w3-account | upload-service (capabilities only) |
| w3-clock | w3clock |
| w3-egress-tracking | etracker (Go) |
| w3-retrieval | Piri (Go) |
| w3-replication | upload-service, Piri (Go) |
| content-serve-auth | freeway, w3up (capabilities) |
| did-mailto | w3up (did-mailto) |
