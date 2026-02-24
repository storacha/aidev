<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# UCAN Auth Model: Patterns & Reference

> **TL;DR:** Spaces (did:key Ed25519) delegate to accounts (did:mailto) via recovery delegation, accounts delegate to agents via session proofs (absent-signed delegation + service attestation via `ucan/attest`). Every invocation carries a proof chain: space -> account -> agent -> service. Email login uses `access/authorize` -> email confirmation -> `access/confirm` -> session proofs -> `access/claim` polling. `did:mailto` accounts have no private key; the service vouches for them.

> Concepts: UCAN delegation chains (P0), proof validation (P0), attestation/sessions (P0), did:mailto (P0), revocation (P0), space management (P0)
> Key repos: w3up (access-client, capabilities, upload-api, did-mailto), ucanto

## How Auth Works in Storacha

```
 Space (did:key)         Account (did:mailto)         Agent (did:key)          Service (did:web)
      |                        |                          |                        |
      |  createRecovery()      |                          |                        |
      |----------------------->|                          |                        |
      |  delegation: space/*   |                          |                        |
      |  iss=space, aud=acct   |                          |                        |
      |                        |                          |                        |
      |                        |   access/authorize       |                        |
      |                        |<-------------------------|                        |
      |                        |   (email sent)           |                        |
      |                        |                          |                        |
      |                        |   access/confirm         |                        |
      |                        |   (user clicks link)     |                        |
      |                        |------------------------->|                        |
      |                        |                          |                        |
      |                        |                          | Session created:       |
      |                        |                          | 1. delegation from     |
      |                        |                          |    did:mailto → agent  |
      |                        |                          |    (absent signature)  |
      |                        |                          | 2. ucan/attest from   |
      |                        |                          |    service (vouches    |
      |                        |                          |    for #1)             |
      |                        |                          |                        |
      |                        |                          | invoke store/add      |
      |                        |                          |----------------------->|
      |                        |                          | proofs: [session,      |
      |                        |                          |  recovery, attest]     |
```

**Key insight:** `did:mailto` accounts have no private key. The service creates delegations on their behalf with an "absent signature" and then issues `ucan/attest` to vouch for the delegation. This is the session mechanism.

## Patterns

### Pattern: Email-based login flow (client side)
**When:** Authorizing an agent with a user's email
**Template:**
```js
import { authorizeAndWait } from '@web3-storage/access/agent'

await authorizeAndWait(agent, 'user@example.com', {
  capabilities: [
    { can: 'space/*' },
    { can: 'store/*' },
    { can: 'upload/*' },
    { can: 'ucan/*' },
    { can: 'plan/*' },
    { can: 'usage/*' },
  ],
})
// Agent now has session proofs — can invoke capabilities
```
**Under the hood:**
1. Agent invokes `access/authorize` with its DID and the email
2. Service sends validation email with link
3. User clicks link → triggers `access/confirm` on server
4. Server creates session proofs (delegation + attestation)
5. Agent polls `access/claim` to retrieve the session proofs
**Key files:** `w3up/packages/access-client/src/agent-use-cases.js:176-199`

### Pattern: Create a session (server side)
**When:** Service confirms an email authorization
**Template:**
```js
import { Absentee } from '@ucanto/principal'
import * as UCAN from '@web3-storage/capabilities/ucan'
import * as Provider from '@ucanto/core/delegation'

async function createSessionProofs({ service, account, agent, capabilities, expiration }) {
  // 1. Create delegation FROM account (absent signature — no private key)
  const delegation = await Provider.delegate({
    issuer: Absentee.from({ id: account.did() }),  // did:mailto, no signature
    audience: agent,                                // did:key of the agent
    capabilities,
    expiration,
  })

  // 2. Service attests the delegation
  const attestation = await UCAN.attest.delegate({
    issuer: service,                    // service signer (did:web)
    audience: agent,
    with: service.did(),
    nb: { proof: delegation.cid },      // CID of the delegation being attested
    expiration,
  })

  return [delegation, attestation]
}
```
**Key files:** `w3up/packages/upload-api/src/access/confirm.js:106-137`
**Gotchas:**
- `Absentee.from({ id: accountDID })` creates a principal with no signing capability — the delegation has a null/absent signature
- The attestation links to the delegation by CID — they're a bonded pair
- Session lifetime: default is `SESSION_LIFETIME` (configurable, typically long-lived)

### Pattern: Create a space
**When:** User creates a new storage space
**Template:**
```js
import { ed25519 as ED25519 } from '@ucanto/principal'

// Generate space identity (Ed25519 keypair → did:key)
const { signer } = await ED25519.generate()
const space = new OwnedSpace({ signer, name: 'my-space' })

// Create recovery delegation (to email account)
const recovery = await space.createRecovery(accountDID)  // did:mailto

// Provision space with account's plan
await account.provision(space.did())

// Store recovery delegation on server
await client.capability.access.delegate({
  space: space.did(),
  delegations: [recovery],
})
```
**Key files:** `w3up/packages/access-client/src/space.js:25-73`, `w3up/packages/w3up-client/src/client.js:275-308`
**Gotchas:**
- Space = Ed25519 keypair. The `did:key` IS the space identifier
- Recovery delegation gives the `did:mailto` account full `space/*` access with no expiration
- Provisioning links the space to a billing plan

### Pattern: Create a delegation
**When:** Granting capabilities to another agent
**Template:**
```js
import { delegate } from '@ucanto/core/delegation'

const delegation = await delegate({
  issuer: agentSigner,           // must have the capability
  audience: recipientDID,        // who gets the delegation
  capabilities: [{
    with: spaceDID,              // resource
    can: 'store/add',            // ability (or 'space/*' for wildcard)
  }],
  proofs: [myProofChain],       // proofs that issuer has this capability
  expiration: Math.floor(Date.now() / 1000) + 3600,  // 1 hour
  facts: [{ space: { name: 'my-space' } }],  // optional metadata
})
```
**Key files:** `w3up/packages/access-client/src/agent.js:427-465`
**Gotchas:**
- Issuer must have proofs for every capability being delegated
- Capabilities can only be attenuated (narrowed), never escalated
- `expiration: Infinity` for never-expiring delegations (used for recovery)
- The agent's `delegate()` method automatically finds proofs from its store

### Pattern: did:mailto DID construction
**When:** Converting email addresses to/from DIDs
**Template:**
```js
import * as DidMailto from '@web3-storage/did-mailto'

const did = DidMailto.fromEmail('user@example.com')
// → 'did:mailto:example.com:user'

const email = DidMailto.toEmail('did:mailto:example.com:user')
// → 'user@example.com'
```
**Key files:** `w3up/packages/did-mailto/src/index.js`
**Gotchas:**
- Format: `did:mailto:<domain>:<local>` (domain BEFORE local part — opposite of email)
- Components are URI-encoded (`encodeURIComponent`)
- Schema: `DID.match({ method: 'mailto' })` or `Account = DID.match({ method: 'mailto' })`

### Pattern: Revoke a UCAN
**When:** Revoking previously granted capabilities
**Template:**
```js
import * as UCAN from '@web3-storage/capabilities/ucan'

const receipt = await UCAN.revoke
  .invoke({
    issuer: agentSigner,
    audience: serviceDID,
    with: agentSigner.did(),
    nb: {
      ucan: delegationToRevoke.cid,       // CID of the UCAN being revoked
      proof: [proofDelegation.cid],        // optional proof chain
    },
    proofs: [delegation],
  })
  .execute(connection)
```
**Key files:** `w3up/packages/capabilities/src/ucan.js:36-75`, `w3up/packages/upload-api/src/ucan/revoke.js`
**Gotchas:**
- Revocation is scoped to a principal — a participant in the delegation can revoke it
- `isParticipant(ucan, principal)` check: issuer or audience can revoke
- Non-participants can also revoke (store as pending), but participants use `reset` (immediate)
- `validateAuthorization()` checks the revocation store for every invocation

### Pattern: Validate authorization (server side)
**When:** Checking if a UCAN invocation is properly authorized
**Template:**
```js
import { validateAuthorization } from './utils/revocation.js'

// In server setup:
Server.create({
  validateAuthorization: async (auth) => {
    // auth contains: delegation, capability, issuer
    const revocationCheck = await validateAuthorization(context, auth)
    if (revocationCheck.error) return revocationCheck
    return { ok: {} }
  },
})
```
**Key files:** `w3up/packages/upload-api/src/utils/revocation.js:20-45`

## Proof Chain Structure

A typical invocation's proof chain for `store/add`:

```
Root: Space (did:key:z6MkSpace...) delegates space/* to Account (did:mailto:example.com:user)
  │   iss=space, aud=account, att=[{can:'space/*', with:space.did()}], exp=Infinity
  │
  ├── Session delegation: Account delegates to Agent (absent signature)
  │   iss=did:mailto:example.com:user, aud=did:key:z6MkAgent, att=[requested caps]
  │
  ├── Attestation: Service attests session delegation
  │   iss=did:web:up.storacha.network, aud=agent, can='ucan/attest', nb={proof: session.cid}
  │
  └── Invocation: Agent invokes store/add
      iss=did:key:z6MkAgent, aud=did:web:up.storacha.network
      att=[{can:'store/add', with:space.did(), nb:{link, size}}]
      prf=[root.cid, session.cid, attestation.cid]
```

## DID Methods Used

| Method | Format | Usage |
|--------|--------|-------|
| `did:key` | `did:key:z6Mk...` (Ed25519) or `did:key:zDn...` (P-256) | Spaces, agents, ephemeral keys |
| `did:mailto` | `did:mailto:domain:user` | User accounts (email-based, no private key) |
| `did:web` | `did:web:up.storacha.network` | Service identities |

## Key Files Index

| Role | File |
|------|------|
| access/authorize capability | `w3up/packages/capabilities/src/access.js:65-80` |
| access/confirm capability | `w3up/packages/capabilities/src/access.js:88-111` |
| access/claim capability | `w3up/packages/capabilities/src/access.js:113-116` |
| ucan/attest capability | `w3up/packages/capabilities/src/ucan.js:130-143` |
| ucan/revoke capability | `w3up/packages/capabilities/src/ucan.js:36-75` |
| Session creation | `w3up/packages/upload-api/src/access/confirm.js:106-137` |
| Claim handler | `w3up/packages/upload-api/src/access/claim.js` |
| Revoke handler | `w3up/packages/upload-api/src/ucan/revoke.js` |
| Revocation validation | `w3up/packages/upload-api/src/utils/revocation.js` |
| Client login flow | `w3up/packages/access-client/src/agent-use-cases.js:176-199` |
| Space generation | `w3up/packages/access-client/src/space.js:25-29` |
| Space authorization | `w3up/packages/access-client/src/space.js:92-109` |
| did:mailto conversion | `w3up/packages/did-mailto/src/index.js` |
| Agent delegation | `w3up/packages/access-client/src/agent.js:427-465` |

## Spec Notes

**UCAN token format:** JWT `<header>.<payload>.<signature>` or DAG-CBOR envelope
- Header: `{alg: "EdDSA", typ: "JWT", ucv: "0.10.0"}`
- Payload: `{iss, aud, exp, att: [{with, can, nb}], prf: [CID...], fct, nnc}`
- Modern (ucanto): DAG-CBOR with IPLD schema types

**Delegation semantics:**
- Chain: each UCAN's `aud` must match next UCAN's `iss`
- Attenuation: capabilities can only be narrowed, never escalated
- Time bounds: `nbf <= now <= exp` for all UCANs in chain

**Storacha extensions to UCAN spec:**
- `ucan/attest` — service attestation for absent-signed delegations (the session mechanism)
- `ucan/revoke` — revocation capability with scoped revocation storage
- `ucan/conclude` — wrapping receipts as capabilities for delegation of receipt-issuing
- `did:mailto` — custom DID method for email-based identities (no private key)

## Design Rationale

- **Email auth without passwords**: `did:mailto` + absent signatures + attestation lets users authorize via email without managing private keys. The service acts as a trusted intermediary.
- **Spaces as DIDs**: Making spaces be `did:key` identities means they have a keypair — they can self-sign root delegations. The space key is the ultimate authority; everything else is delegated.
- **Recovery via did:mailto**: Storing a never-expiring delegation to the user's email account means even if they lose their device, they can re-authorize via email.
- **Attestation over DKIM**: Rather than verifying DKIM signatures in the delegation chain (complex, fragile), the service simply attests that it verified the email. Simpler trust model.

## Authoritative Specs
- [UCAN Spec (v1.0 RC)](https://github.com/ucan-wg/spec)
- [UCAN Delegation Spec](https://github.com/ucan-wg/delegation)
- [did:mailto Method](https://github.com/storacha/specs/blob/main/did-mailto.md)
- [W3 Access Spec](https://github.com/storacha/specs/blob/main/w3-access.md)
- [W3 Session Spec](https://github.com/storacha/specs/blob/main/w3-session.md)
