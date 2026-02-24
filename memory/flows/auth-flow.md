<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Auth Flow: End-to-End Trace

> **TL;DR:** Three phases: (A) Space creation -- generate Ed25519 keypair, create recovery delegation to did:mailto, provision with billing plan. (B) Email login -- `access/authorize` -> email sent -> user clicks -> `access/confirm` creates session proofs (absent-signed delegation + `ucan/attest`) -> agent polls `access/claim`. (C) Invocation -- agent signs with proof chain (recovery + session + attestation), server validates chain + checks revocations.

## Overview

```
A. Space Creation          B. Email Login              C. Capability Invocation

1. ED25519.generate()      1. access/authorize         1. Agent invokes blob/add
   → space (did:key)          (agent DID + email)         with proofs:
2. space.createRecovery()  2. Email sent to user          [recovery, session, attest]
   → delegation to         3. User clicks link         2. Server validates chain:
     did:mailto            4. access/confirm              space→account→agent→service
3. provider/add               → session proofs          3. Revocation check
   → provision space       5. access/claim              4. Handler executes
4. access/delegate            → agent gets proofs
   → store recovery
```

## A. Space Creation

### Step 1: Generate Space Identity

| | |
|---|---|
| **File** | `w3up/packages/access-client/src/space.js` |
| **Function** | `OwnedSpace` constructor, uses `ed25519.generate()` |

```js
const { signer } = await ED25519.generate()  // → Ed25519 keypair
const space = new OwnedSpace({ signer, name: 'my-space' })
// space.did() → did:key:z6Mk...
```

### Step 2: Create Recovery Delegation

| | |
|---|---|
| **File** | `w3up/packages/access-client/src/space.js` → `createRecovery()` |
| **Delegation** | `space/*` from space to did:mailto account, expiration: Infinity |

```js
const recovery = await space.createRecovery(accountDID)
// iss: space (did:key), aud: account (did:mailto), att: [{can: 'space/*', with: space.did()}]
```

### Step 3: Provision Space

| | |
|---|---|
| **File** | `w3up/packages/access-client/src/account.js` → `provision()` |
| **Capability** | `provider/add` |
| **Infra** | `provisionsStorage` (DynamoDB) |

Links space to account's billing plan.

### Step 4: Store Recovery Delegation

| | |
|---|---|
| **Capability** | `access/delegate` |
| **Infra** | DynamoDB (`delegationsTable`) + R2 (`delegationsBucket`) |

Delegations are stored as CAR-encoded bytes in R2, indexed by audience in DynamoDB.

## B. Email Login Flow

### Step 1: access/authorize

| | |
|---|---|
| **Client** | `w3up/packages/access-client/src/agent-use-cases.js` → `authorizeAndWait()` |
| **Server** | `w3up/packages/upload-api/src/access/authorize.js` |
| **Capability** | `access/authorize` with `nb: { iss: agentDID, att: [requested capabilities] }` |

1. Client sends agent DID + requested capabilities
2. Server validates and creates a `access/confirm` delegation
3. Server sends email with confirmation link containing the delegation
4. Returns `{ expiration }` (how long the confirmation is valid)

### Step 2: User Clicks Email Link

The email contains a URL that triggers `access/confirm`.

### Step 3: access/confirm

| | |
|---|---|
| **File** | `w3up/packages/upload-api/src/access/confirm.js` |
| **Capability** | `access/confirm` with `nb: { iss: accountDID, aud: agentDID, att: [caps], cause: authorizeCID }` |
| **Function** | `confirm()` → `createSessionProofs()` |

Creates two things:

**Session delegation** (absent signature):
```js
const delegation = await Provider.delegate({
  issuer: Absentee.from({ id: account.did() }),  // did:mailto — no private key
  audience: agent,                                 // did:key of requesting agent
  capabilities: requestedCapabilities,             // e.g., [{can: 'space/*', with: 'ucan:*'}]
  expiration: Infinity,
})
```

**Service attestation**:
```js
const attestation = await UCAN.attest.delegate({
  issuer: service,                    // service signer (did:web)
  audience: agent,                    // did:key of requesting agent
  with: service.did(),
  nb: { proof: delegation.cid },     // links to the session delegation by CID
  expiration: Infinity,
})
```

Both are stored via `delegationsStorage.putMany([delegation, attestation])`.

### Step 4: access/claim

| | |
|---|---|
| **Client** | `w3up/packages/access-client/src/agent-use-cases.js` (polls until proofs available) |
| **Server** | `w3up/packages/upload-api/src/access/claim.js` |
| **Capability** | `access/claim` |
| **Infra** | DynamoDB (delegations table) + R2 (delegations bucket) |

1. Agent polls `access/claim` periodically
2. Server queries `delegationsStorage.find({ audience: agent.did() })`
3. Returns all delegations for that agent (session + attestation + any space delegations)
4. Agent stores proofs in its local proof store

## C. Capability Invocation & Validation

### Proof Chain for an Invocation

When agent invokes e.g. `blob/add`:

```
Invocation: agent → service
  att: [{can: 'blob/add', with: spaceDID, nb: {blob}}]
  proofs:
    ├── Recovery: space → account (space/* delegation, exp: Infinity)
    ├── Session: account → agent (space/* delegation, absent signature)
    └── Attestation: service attests session (ucan/attest, nb: {proof: session.cid})
```

### Server Validation

| | |
|---|---|
| **File** | `ucanto/packages/server/src/server.js` → validates before routing |
| **Revocation check** | `w3up/packages/upload-api/src/utils/revocation.js` |

1. Decode CAR-encoded invocation
2. Verify invocation signature (agent's ed25519 key)
3. Walk proof chain: agent ← account ← space (checking `aud` matches `iss` at each step)
4. Verify attestation: service signed `ucan/attest` for the session delegation CID
5. Check capability attenuation: requested caps must be subset of delegated caps
6. **Revocation check**: query revocation store for any revoked delegations in the chain
7. Route to handler based on capability `can` field

### Revocation

| | |
|---|---|
| **File** | `w3up/packages/upload-api/src/ucan/revoke.js` |
| **Capability** | `ucan/revoke` with `nb: { ucan: delegationCID }` |

- Participants (issuer or audience of the delegation) can revoke immediately
- Non-participants can submit revocation (stored as pending)
- `validateAuthorization()` checks revocation store on every invocation

## Infrastructure

| Component | Storage | Purpose |
|-----------|---------|---------|
| Delegations table | DynamoDB | Index: audience → delegation CID, issuer, expiration |
| Delegations bucket | R2/S3 | Store CAR-encoded delegation bytes |
| Provisions | DynamoDB | Space → storage provider mapping |
| Revocations | DynamoDB | Revoked delegation CIDs |
| Agent proof store | Client-side (IndexedDB) | Local cache of proofs |

## Key Files

| Role | File |
|------|------|
| Space creation | `w3up/packages/access-client/src/space.js` |
| Agent use cases | `w3up/packages/access-client/src/agent-use-cases.js` |
| access/authorize handler | `w3up/packages/upload-api/src/access/authorize.js` |
| access/confirm handler | `w3up/packages/upload-api/src/access/confirm.js` |
| access/claim handler | `w3up/packages/upload-api/src/access/claim.js` |
| access/delegate handler | `w3up/packages/upload-api/src/access/delegate.js` |
| Session proofs | `w3up/packages/upload-api/src/access/confirm.js:createSessionProofs` |
| Revocation handler | `w3up/packages/upload-api/src/ucan/revoke.js` |
| Revocation validation | `w3up/packages/upload-api/src/utils/revocation.js` |
| Delegations table (w3infra) | `w3infra/upload-api/tables/delegations.js` |
| Delegations bucket (w3infra) | `w3infra/upload-api/buckets/delegations-store.js` |
| did:mailto | `w3up/packages/did-mailto/src/index.js` |
