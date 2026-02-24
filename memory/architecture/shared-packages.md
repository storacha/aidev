<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Shared Packages & Blast Radius Analysis

> **TL;DR:** EXTREME caution (15+ repos): `@ucanto/core`, `@ucanto/interface`, `@ucanto/principal`, `@ucanto/transport`, `@ipld/car`. HIGH caution (10+): `@storacha/capabilities`, `@ucanto/server`, `@ucanto/client`. Go equivalents: `go-ucanto` (12 repos), `go-libstoracha` (11 repos). Safe: adding new capabilities. Dangerous: changing existing capability schemas, modifying `@ucanto/*` wire format. Two monorepos (`upload-service` @storacha/* and `w3up` @web3-storage/*) share 8 packages; prefer `upload-service` for active work.

## Monorepo Relationship

Two monorepos contain the same core packages under different namespaces:

| `upload-service` (@storacha/*) | `w3up` (@web3-storage/*) | Status |
|---|---|---|
| @storacha/capabilities | @web3-storage/capabilities | **upload-service is newer** |
| @storacha/upload-api | @web3-storage/upload-api | upload-service is newer |
| @storacha/upload-client | @web3-storage/upload-client | upload-service is newer |
| @storacha/access | @web3-storage/access | upload-service is newer |
| @storacha/blob-index | @web3-storage/blob-index | upload-service is newer |
| @storacha/filecoin-api | @web3-storage/filecoin-api | upload-service is newer |
| @storacha/filecoin-client | @web3-storage/filecoin-client | upload-service is newer |
| @storacha/did-mailto | @web3-storage/did-mailto | upload-service is newer |

**upload-service exclusive packages:** @storacha/cli, @storacha/console, @storacha/encrypt-upload-client, @storacha/principal-resolver, @storacha/router, @storacha/ucn, @storacha/client (renamed from w3up-client)

**Rule:** For active development, prefer the `upload-service` repo (`@storacha/*` namespace). The `w3up` repo (`@web3-storage/*`) is the legacy version. Some external repos still import `@web3-storage/*` and haven't migrated yet.

---

## Highest Blast-Radius JS Packages

### Tier 1: Change triggers 15+ repos (EXTREME caution)

| Package | Dependents | What it provides |
|---|---|---|
| **@ucanto/core** | 23 repos | UCAN invocation/delegation/receipt types, encoding, block model |
| **@ucanto/interface** | 20 repos | TypeScript type definitions for all ucanto abstractions |
| **@ucanto/principal** | 20 repos | Ed25519/P-256 signer/verifier, DID parsing |
| **@ucanto/transport** | 20 repos | CAR-encoded HTTP transport, legacy codec |
| **@ipld/car** | 20 repos | CAR file reading/writing |

**Impact of changes:**
- `@ucanto/*` changes affect virtually every service and client in the ecosystem
- Breaking changes here break the entire UCAN RPC layer
- These packages are in the `ucanto` repo — treated as infrastructure, rarely changed

### Tier 2: Change triggers 10-18 repos (HIGH caution)

| Package | Dependents | What it provides |
|---|---|---|
| **@ucanto/client** | 18 repos | Client-side UCAN invocation builder |
| **@ipld/dag-cbor** | 18 repos | DAG-CBOR codec (primary block encoding) |
| **@ipld/dag-ucan** | 16 repos | UCAN token encoding/decoding |
| **@ipld/dag-json** | 16 repos | DAG-JSON codec (used for queues, debugging) |
| **@storacha/client** | 12 repos | High-level client SDK (was w3up-client) |
| **@storacha/capabilities** | 11 repos | All UCAN capability definitions |
| **@ucanto/server** | 11 repos | Server-side handler routing, provide/provideAdvanced |

**Impact of changes:**
- `@storacha/capabilities` is the most impactful application-level package — every capability change radiates to all services
- Adding a new capability is safe (additive). Changing an existing capability's schema breaks consumers.
- `@ucanto/server` changes affect all service implementations

### Tier 3: Change triggers 5-10 repos (MODERATE caution)

| Package | Dependents | What it provides |
|---|---|---|
| **@ucanto/validator** | 10 repos | Proof chain validation, authorization |
| **@web3-storage/content-claims** | 9 repos | Content claims client library |
| **@ipld/dag-pb** | 8 repos | UnixFS block encoding |
| **@storacha/access** | 7 repos | Agent/space management, login flow |
| **@storacha/blob-index** | 7 repos | ShardedDAGIndex encode/decode |
| **@web3-storage/data-segment** | 6 repos | CommP/FR32 computation |
| **@ipld/unixfs** | 6 repos | UnixFS encode/decode streams |
| **@storacha/indexing-service-client** | 6 repos | Indexing service query client |
| **@storacha/upload-client** | 5 repos | Upload orchestration (shard, blob/add, index/add) |

---

## Highest Blast-Radius Go Modules

| Module | Dependents | What it provides |
|---|---|---|
| **go-ucanto** | 12 repos | Go UCAN implementation (server, client, transport) |
| **go-libstoracha** | 11 repos | Go capability definitions, IPNI publisher, claim types |
| **filecoin-services/go** | 4 repos | Filecoin PDP service interfaces |
| **indexing-service** | 3 repos | Content routing + claims |

**Rule:** Changes to `go-ucanto` or `go-libstoracha` affect virtually all Go services. Same caution as `@ucanto/*` in JS.

---

## w3up/upload-service Internal Dependency Tree

```
@storacha/capabilities (FOUNDATION — every other package depends on this)
    ↑
    ├── @storacha/blob-index
    ├── @storacha/filecoin-client
    ├── @storacha/access (+ did-mailto)
    ├── @storacha/upload-client (+ blob-index, filecoin-client)
    ├── @storacha/filecoin-api (+ filecoin-client)
    ├── @storacha/upload-api (+ access, blob-index, did-mailto, filecoin-api)
    └── @storacha/client (+ access, upload-client, upload-api, blob-index,
                           did-mailto, filecoin-client, capabilities)
```

**Change propagation:**
1. Change `capabilities` → rebuilds everything
2. Change `blob-index` → rebuilds upload-client, upload-api, client
3. Change `filecoin-client` → rebuilds filecoin-api, upload-client, client
4. Change `access` → rebuilds upload-api, client
5. Change `upload-api` → rebuilds client
6. Change `upload-client` → rebuilds client

---

## Cross-Repo Capability Contract Boundaries

When you modify a **capability definition** in `@storacha/capabilities`, these services must be checked:

| Capability group | Handler repos | Client repos |
|---|---|---|
| `blob/*`, `space/blob/*` | upload-service (upload-api), piri (Go) | upload-service (upload-client), freeway, w3infra |
| `upload/*` | upload-service (upload-api) | upload-service (upload-client), w3cli |
| `filecoin/*`, `piece/*`, `aggregate/*`, `deal/*` | upload-service (filecoin-api), w3filecoin-infra | upload-service (filecoin-client) |
| `access/*` | upload-service (upload-api), freeway | upload-service (access-client), w3cli, ucan-kms |
| `space/info` | upload-service (upload-api) | upload-service (access-client) |
| `space/content/serve/*` | freeway | freeway, w3infra |
| `space/index/*` | upload-service (upload-api), indexing-service | upload-service (upload-client) |
| `ucan/*` | upload-service (upload-api), ucanto | All clients |
| `plan/*` | upload-service (upload-api) | w3cli, dashboard |
| `rate-limit/*` | upload-service (upload-api) | admin |
| `clock/*` | w3clock | w3clock (self-contained) |
| `assert/*` | content-claims, indexing-service | upload-service, freeway, blob-fetcher |
| `claim/*` | indexing-service | piri, delegator |
| `space/encryption/*` | ucan-kms | upload-service (encrypt-upload-client) |
| `space/content/retrieve` | piri (Go) | guppy (Go) |
| `space/egress/*` | etracker (Go) | piri (Go) |
| `blob/replica/*` | piri (Go) | upload-service |

---

## Version Coupling Rules

1. **Monorepo packages (w3up / upload-service):** All packages in a monorepo are versioned together via changesets. A PR touching `capabilities` will trigger version bumps in all dependents within the monorepo.

2. **ucanto packages:** Versioned independently but tightly coupled. A breaking change in `@ucanto/core` requires coordinated updates across `interface`, `server`, `client`, `transport`, `validator`, `principal`.

3. **Go modules:** Use Go module versioning (SemVer). `go-ucanto` and `go-libstoracha` changes require `go get -u` in all dependent repos.

4. **Cross-repo JS deps:** External repos (freeway, w3infra, admin, etc.) pin specific versions via `npm`/`pnpm`. Breaking changes require coordinated PRs across repos.

---

## Safe vs Dangerous Changes

### Safe (additive, backward-compatible)
- Adding a new capability to `@storacha/capabilities` (new `can` string)
- Adding new optional fields (`nb` caveats) to existing capabilities
- Adding new handler for an existing capability
- Adding a new export to a package

### Dangerous (breaking, wide blast radius)
- Changing the schema of an existing capability's `nb` fields
- Renaming a capability's `can` string
- Changing `@ucanto/*` wire format or encoding
- Removing or renaming exports from `@storacha/capabilities`
- Changing `go-ucanto` or `go-libstoracha` API signatures
- Modifying shared type definitions (TypeScript interfaces in `types.ts`)

### Requires Coordination
- Changing the UCAN validation logic (`@ucanto/validator`)
- Changing transport encoding (`@ucanto/transport`)
- Modifying content claims schema (`content-claims`)
- Changing ShardedDAGIndex format (`@storacha/blob-index`)

---

## Service-to-Service Connections

Derived from 231 service graph edges across all repos. This maps which services call which, the mechanism used, and the key capabilities exchanged.

### Upload Service (hub, 74 outbound edges)

Upload-service is the central orchestrator. It connects to nearly every other service:

| Target Service | Mechanism | Capabilities | Purpose |
|---------------|-----------|--------------|---------|
| **Filecoin pipeline** (Storefront, Aggregator, Dealer, DealTracker) | ucanto RPC | `filecoin/submit`, `filecoin/accept`, `piece/offer`, `piece/accept`, `aggregate/offer`, `aggregate/accept`, `deal/info` | Submits pieces to Filecoin deal pipeline |
| **w3clock** | ucanto RPC | `clock/advance`, `clock/head` | Merkle clock operations for space state |
| **Content claims** (via assert) | ucanto RPC | `assert/equals` | Issues content equality claims |
| **UCAN KMS** | ucanto connection | `space/encryption/key/decrypt`, `space/encryption/setup` | Encryption key management for encrypted uploads |
| **Internal blob ops** (W3sBlob) | ucanto RPC | `web3.storage/blob/allocate`, `web3.storage/blob/accept`, `http/put` | Service-internal blob lifecycle |
| **Self (Upload API)** | ucanto RPC | `space/blob/add`, `blob/remove`, `blob/replicate`, `upload/add`, `upload/remove`, `upload/list`, `upload/get`, `index/add`, `blob/list`, `blob/get` | Client-facing capability invocations |
| **Access service** | ucanto RPC | `access/confirm` | Email confirmation flow |
| **Revocation service** | HTTP fetch | - | Check delegation revocations |

### w3infra (15 outbound edges)

| Target Service | Mechanism | Capabilities | Purpose |
|---------------|-----------|--------------|---------|
| **Filecoin Storefront** | ucanto RPC | `filecoin/submit`, `filecoin/accept` | Pipeline submissions from DynamoDB stream handlers |
| **Upload API** | ucanto connection | - | Routes invocations to upload-api Lambda |
| **Access service** | ucanto RPC | `access/confirm` | Confirm access delegations |
| **Humanode** | HTTP fetch | - | Token endpoint for identity verification |
| **SQS queues** | queue | - | Internal pipeline queuing |

### Freeway (7 outbound edges)

| Target Service | Mechanism | Capabilities | Purpose |
|---------------|-----------|--------------|---------|
| **Upload API** | ucanto RPC | `space/content/serve/egress/record` | Record egress events for billing |
| **Self** | ucanto RPC | `space/content/serve/transport/http` | Authorize content serving |
| **Egress queue** (CF Queue) | queue | - | Async egress event tracking |

### Content Claims (11 outbound edges)

| Target Service | Mechanism | Capabilities | Purpose |
|---------------|-----------|--------------|---------|
| **Self** (claim issuing) | ucanto RPC | `assert/location`, `assert/partition`, `assert/inclusion`, `assert/index`, `assert/relation`, `assert/equals` | Issues all 6 assertion claim types |

Content-claims is primarily a self-contained service that issues and stores claims. Other services query it via HTTP GET, not ucanto.

### UCAN KMS (4 outbound edges)

| Target Service | Mechanism | Capabilities | Purpose |
|---------------|-----------|--------------|---------|
| **Upload API** | ucanto RPC | `plan/get` | Check user plan for encryption feature access |
| **Google Cloud KMS** | HTTP fetch | - | Actual key operations (encrypt, decrypt, create key versions) |

### Go Services (minimal outbound edges)

| Service | Edges | Mechanism | Notes |
|---------|-------|-----------|-------|
| **Piri** | 3 | go HTTP | HTTP PUT for blob uploads to external storage |
| **Indexing Service** | 2 | go HTTP | HTTP GET for fetching content from external sources |
| **Etracker** | 1 | go HTTP | HTTP for egress event submission |

Go services primarily **receive** ucanto invocations (as servers) rather than making outbound ucanto calls. Their outbound traffic is mostly plain HTTP to blob storage and external APIs.

### Connection Patterns Summary

1. **ucanto RPC** (dominant): Most service-to-service communication uses signed UCAN invocations over CAR-encoded HTTP. This provides authorization by default.
2. **ucanto_connection** (configuration): Connection setup (DID + URL pairs) for establishing ucanto channels.
3. **HTTP fetch**: Used for non-UCAN external APIs (Google KMS, Humanode, revocation checks).
4. **Cloudflare Queues**: Freeway uses CF Queues for async egress tracking.
5. **SQS Queues**: w3infra uses SQS for internal pipeline processing.
6. **CF Service Bindings**: reads/w3link use Cloudflare service bindings for Worker-to-Worker direct calls.

---

## Downstream Consumers

These repos are **consumer applications** that depend on `@storacha/client` (or the legacy `@web3-storage/w3up-client`) and would break if the client SDK API changes. Grouped by risk level.

### Direct SDK Consumers (would break on @storacha/client API changes)

| Repo | Product | Role | Deploy Target | Risk |
|------|---------|------|---------------|------|
| **console-toolkit** | Developer Tools | Documentation/SDK wrapper | - | HIGH -- developer-facing SDK examples |
| **dashboard** | Developer Tools | Web app | - | HIGH -- user-facing upload UI |
| **tg-miniapp** | Developer Tools | Telegram mini-app | Docker | MEDIUM -- end-user app |
| **bluesky-backup-webapp-server** | Legacy | Bluesky backup webapp | Docker | MEDIUM -- integrates upload flow |
| **admin** | Legacy | Admin dashboard | - | LOW -- internal tool |
| **agent-store-migration** | Legacy | Migration tool | - | LOW -- one-time migration |
| **ai-integrations** | AI & Integrations | AI plugin examples | - | LOW -- documentation/examples |

### Infrastructure Consumers (depend on upload-service packages but not the client SDK directly)

| Repo | Product | Dependency | Risk |
|------|---------|------------|------|
| **w3infra** | Upload Platform | `upload-service` + `w3up` | CRITICAL -- production infra |
| **freeway** | Gateway & Retrieval | `upload-service` (capabilities) | CRITICAL -- production gateway |
| **blob-fetcher** | Gateway & Retrieval | `upload-service` (capabilities) | HIGH -- retrieval pipeline |
| **w3filecoin-infra** | Filecoin Pipeline | `upload-service` (filecoin-api) | HIGH -- Filecoin infra |
| **ucan-kms** | Identity & Auth | `upload-service` (capabilities) | MEDIUM -- encryption service |
| **content-claims** | Content Routing | `w3up` (capabilities) | HIGH -- claims service |
| **hoverboard** | Gateway & Retrieval | `w3up` (capabilities) | MEDIUM -- Bitswap gateway |

### Assessment

- **7 repos** directly consume the client SDK (potential UI/UX breakage on API changes)
- **7 repos** consume lower-level packages from upload-service/w3up (potential service breakage)
- The highest-risk consumer is **w3infra** which depends on both `upload-service` and `w3up` packages and runs the production Upload API
- **dashboard** and **console-toolkit** are the most user-visible consumer apps
