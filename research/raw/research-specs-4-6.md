# Research Report: Storacha Specifications (Topics 4-6)

## Table of Contents

- [Topic 4: UCAN Auth Model](#topic-4-ucan-auth-model)
  - [4.1 DID Methods](#41-did-methods)
    - [4.1.1 did:key Method](#411-didkey-method)
    - [4.1.2 did:web Method](#412-didweb-method)
    - [4.1.3 did:mailto Method](#413-didmailto-method)
  - [4.2 UCAN Delegation Semantics](#42-ucan-delegation-semantics)
    - [4.2.1 UCAN Token Structure](#421-ucan-token-structure)
    - [4.2.2 Delegation Chain and Principal Alignment](#422-delegation-chain-and-principal-alignment)
    - [4.2.3 Proof Verification Traversal](#423-proof-verification-traversal)
  - [4.3 UCAN Revocation](#43-ucan-revocation)
    - [4.3.1 Core UCAN Revocation Spec](#431-core-ucan-revocation-spec)
    - [4.3.2 Storacha ucan/revoke Extension](#432-storacha-ucanrevoke-extension)
  - [4.4 Storacha Authorization Flow (w3-session)](#44-storacha-authorization-flow-w3-session)
    - [4.4.1 Step-by-Step Authorization Flow](#441-step-by-step-authorization-flow)
    - [4.4.2 Authorization Session (ucan/attest)](#442-authorization-session-ucanattest)
    - [4.4.3 Attestation Signature Mechanism](#443-attestation-signature-mechanism)
  - [4.5 W3 Access Protocol](#45-w3-access-protocol)
    - [4.5.1 access/delegate](#451-accessdelegate)
    - [4.5.2 access/claim](#452-accessclaim)
    - [4.5.3 access/request](#453-accessrequest)
  - [4.6 W3 Account Protocol](#46-w3-account-protocol)
    - [4.6.1 Account Concept and Roles](#461-account-concept-and-roles)
    - [4.6.2 Signature Types for did:mailto](#462-signature-types-for-didmailto)
    - [4.6.3 Multi-Device Access Pattern](#463-multi-device-access-pattern)
- [Topic 5: Content Claims and Indexing](#topic-5-content-claims-and-indexing)
  - [5.1 Content Claims Protocol](#51-content-claims-protocol)
    - [5.1.1 Location Claim (assert/location)](#511-location-claim-assertlocation)
    - [5.1.2 Inclusion Claim (assert/inclusion)](#512-inclusion-claim-assertinclusion)
    - [5.1.3 Index Claim (assert/index)](#513-index-claim-assertindex)
    - [5.1.4 Partition Claim (assert/partition)](#514-partition-claim-assertpartition)
    - [5.1.5 Equivalency Claim (assert/equals)](#515-equivalency-claim-assertequals)
    - [5.1.6 Relation Claim (assert/relation)](#516-relation-claim-assertrelation)
  - [5.2 IPNI (InterPlanetary Network Indexer)](#52-ipni-interplanetary-network-indexer)
    - [5.2.1 Overview and Architecture](#521-overview-and-architecture)
    - [5.2.2 Advertisement Chain Structure](#522-advertisement-chain-structure)
    - [5.2.3 Advertisement Schema Fields](#523-advertisement-schema-fields)
    - [5.2.4 Entry Chunks and Multihash Lists](#524-entry-chunks-and-multihash-lists)
    - [5.2.5 Announcements](#525-announcements)
    - [5.2.6 Provider Records and Lookups](#526-provider-records-and-lookups)
  - [5.3 Sharded DAG Index](#53-sharded-dag-index)
    - [5.3.1 Index Schema (index/sharded/dag@0.1)](#531-index-schema-indexshardeddag01)
    - [5.3.2 BlobIndex and BlobSlice Types](#532-blobindex-and-blobslice-types)
    - [5.3.3 How CIDs Map to Byte Ranges in Blobs](#533-how-cids-map-to-byte-ranges-in-blobs)
  - [5.4 W3 Blob Protocol](#54-w3-blob-protocol)
    - [5.4.1 Blob Add Workflow](#541-blob-add-workflow)
    - [5.4.2 Location Commitment](#542-location-commitment)
  - [5.5 W3 Index Protocol (space/index/add)](#55-w3-index-protocol-spaceindexadd)
- [Topic 6: Filecoin Pipeline](#topic-6-filecoin-pipeline)
  - [6.1 Filecoin Proofs Overview](#61-filecoin-proofs-overview)
    - [6.1.1 Proof of Replication (PoRep) and Sealing](#611-proof-of-replication-porep-and-sealing)
    - [6.1.2 Proof of Spacetime (PoSt)](#612-proof-of-spacetime-post)
    - [6.1.3 Proof of Data Possession (PDP)](#613-proof-of-data-possession-pdp)
  - [6.2 CommP (Piece Commitment) Computation](#62-commp-piece-commitment-computation)
    - [6.2.1 FR32 Padding Algorithm](#621-fr32-padding-algorithm)
    - [6.2.2 Power-of-Two Padding](#622-power-of-two-padding)
    - [6.2.3 Merkle Tree Construction and CommP](#623-merkle-tree-construction-and-commp)
    - [6.2.4 Piece Sizes and Alignment](#624-piece-sizes-and-alignment)
  - [6.3 FRC-0058: Verifiable Data Aggregation](#63-frc-0058-verifiable-data-aggregation)
    - [6.3.1 Problem Statement](#631-problem-statement)
    - [6.3.2 Data Segments](#632-data-segments)
    - [6.3.3 Aggregation Scheme](#633-aggregation-scheme)
    - [6.3.4 Inclusion Proofs (DataAggregationProof)](#634-inclusion-proofs-dataaggregationproof)
    - [6.3.5 Piece Multihash CID (fr32-sha2-256-trunc254-padded-binary-tree)](#635-piece-multihash-cid-fr32-sha2-256-trunc254-padded-binary-tree)
  - [6.4 W3 Filecoin Protocol (Storacha Pipeline)](#64-w3-filecoin-protocol-storacha-pipeline)
    - [6.4.1 Roles in the Pipeline](#641-roles-in-the-pipeline)
    - [6.4.2 Pipeline Flow Step by Step](#642-pipeline-flow-step-by-step)
    - [6.4.3 Storefront Capabilities](#643-storefront-capabilities)
    - [6.4.4 Aggregator Capabilities](#644-aggregator-capabilities)
    - [6.4.5 Dealer Capabilities](#645-dealer-capabilities)
    - [6.4.6 Deal Tracker Capabilities](#646-deal-tracker-capabilities)
    - [6.4.7 Inclusion Proof Structure](#647-inclusion-proof-structure)

---

# Topic 4: UCAN Auth Model

## 4.1 DID Methods

### 4.1.1 did:key Method

**Source**: [W3C CCG did:key spec v0.9](https://w3c-ccg.github.io/did-key-spec/)

The `did:key` method is a purely generative DID method -- no registry lookup is needed. A DID is created directly from a cryptographic public key. The format is:

```
did:key:<multibase-encoded-multicodec-public-key>
```

**Encoding formula:**

```
did:key:MULTIBASE(base58-btc, MULTICODEC(public-key-type, raw-public-key-bytes))
```

**Ed25519 keys:**
- Multicodec prefix: `0xed01` (2 bytes)
- Followed by the 32-byte raw Ed25519 public key
- Base58-btc encoding with `z` multibase prefix
- Example: `did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK`

**P-256 (secp256r1) keys:**
- Multicodec prefix: `0x1200` (varint encoded)
- Followed by the 33-byte compressed P-256 public key
- Also base58-btc encoded with `z` prefix
- Supports both compressed (33 byte with 02/03 prefix) and uncompressed (65 byte with 04 prefix) forms

**DID Document generation:**
- The DID Document is generated algorithmically from the key -- no resolution against a registry is needed.
- Contains a `verificationMethod` with the public key.
- For Ed25519 keys, an `X25519` key agreement key is derived using the birational map from Ed25519 to Curve25519.
- The DID document includes `authentication`, `assertionMethod`, `capabilityDelegation`, and `capabilityInvocation` verification relationships.

**Key properties:**
- Stateless and deterministic -- identical keys always produce identical DIDs
- Cannot be updated or deactivated (immutable)
- Used in Storacha for agent identifiers and space identifiers

### 4.1.2 did:web Method

**Source**: [W3C CCG did:web spec](https://w3c-ccg.github.io/did-method-web/)

The `did:web` method uses a web domain as the basis for a DID. The DID document is hosted at a well-known URL on the domain.

**Format:**
```
did:web:<domain>[:<path>]
```

**Resolution process:**
1. Replace colons in method-specific identifier with forward slashes to construct a URL path
2. If no path is specified, append `/.well-known`
3. Append `/did.json` to complete the URL
4. Perform an HTTPS GET request to retrieve the DID document

**Examples:**
- `did:web:web3.storage` resolves to `https://web3.storage/.well-known/did.json`
- `did:web:w3c-ccg.github.io:user:alice` resolves to `https://w3c-ccg.github.io/user/alice/did.json`

**Usage in Storacha:**
- Used for service/authority identifiers (e.g., `did:web:web3.storage`, `did:web:up.storacha.network`)
- The Storefront, Aggregator, Dealer, and Deal Tracker services are identified by `did:web` identifiers
- Allows key rotation without changing the DID (unlike `did:key`)

**Security note:** Whoever controls the domain controls the DID. Verification with signed data proves control of the private keys corresponding to the DID document, but domain-level trust is assumed.

### 4.1.3 did:mailto Method

**Source**: `specs/did-mailto.md`

The `did:mailto` method is a custom DID method used by Storacha for email-based account identifiers. It enables human-meaningful identifiers that users can type on any device.

**Format:**
```abnf
did = "did:mailto:" domain-name ":" user-name
```

The local-part of the email is percent-encoded if it contains special characters.

**Examples:**
- `jsmith@example.com` becomes `did:mailto:example.com:jsmith`
- `tag+alice@web.mail` becomes `did:mailto:web.mail:tag%2Balice`

**How did:mailto works:**

1. **Create (Register):**
   - Create a `did:key` identifier
   - Send an email from the DID subject's email address with a key authentication message in the subject line: `"I am also known as did:key:z6Mk..."`
   - The email's DKIM signature provides cryptographic proof linking the email address to the key

2. **Read (Resolve):**
   - Extract the key authentication from the email `Subject` header
   - Extract the `did:key` from the authentication message
   - Extract the sender email from the `From` header
   - Resolve the DID Document from the extracted `did:key`
   - Set the `id` to the `did:mailto` identifier
   - Set `alsoKnownAs` to the extracted `did:key`

3. **Deactivate (Revoke):**
   - Send an email with subject: `"I revoke did:key:z6Mk..."`

**Key properties:**
- No private key exists for `did:mailto` -- signing happens via DKIM or attestation signatures
- Designed to work alongside `did:key` for bootstrapping sessions across multiple devices
- More accessible than `did:web` since almost everyone has an email address
- Verifiable offline when the domain key (DKIM) is known

## 4.2 UCAN Delegation Semantics

### 4.2.1 UCAN Token Structure

**Source**: [UCAN Specification](https://github.com/ucan-wg/spec), [ucan.xyz/specification](https://ucan.xyz/specification/)

A UCAN (User Controlled Authorization Network) token is a signed JWT-like structure encoded in IPLD. Key fields:

| Field | Description |
|-------|-------------|
| `v`   | UCAN version (e.g., `"0.9.1"`) |
| `iss` | Issuer DID -- the principal delegating capabilities; signer of the UCAN |
| `aud` | Audience DID -- the principal receiving the delegation |
| `att` | Capabilities being delegated (array of `{can, with, nb}` objects) |
| `prf` | Proof chain -- links to parent UCANs that authorize this delegation |
| `exp` | Expiration (Unix timestamp or `null` for no expiry) |
| `nbf` | Not-before time (optional) |
| `nnc` | Nonce for uniqueness (optional) |
| `fct` | Facts -- additional metadata (optional) |
| `s`   | Signature bytes |

**Capability structure:**
```json
{
  "can": "store/add",           // ability name (hierarchical namespace)
  "with": "did:key:zSpace",    // resource URI
  "nb": { ... }                 // caveats/constraints (optional)
}
```

Abilities use hierarchical namespaces with `/` separators. A `*` ability represents superuser access.

### 4.2.2 Delegation Chain and Principal Alignment

**Source**: [UCAN Spec - Principal Alignment](https://github.com/ucan-wg/spec/blob/main/README.md#62-principal-alignment)

UCAN delegation forms a chain of trust from the resource owner to the invoker. The critical rule is **principal alignment**:

> The `aud` field of every proof MUST match the `iss` field of the UCAN that includes it in `prf`.

This means:
1. If Alice (`did:key:zAlice`) delegates to Bob (`did:key:zBob`), then `iss=zAlice, aud=zBob`
2. If Bob further delegates to Carol (`did:key:zCarol`), Bob's UCAN has `iss=zBob, aud=zCarol`, and Bob's proof chain (`prf`) includes Alice's UCAN where `aud=zBob`
3. The chain must form an unbroken path from the resource subject back to the invoker

**Delegation chain example:**
```
Space (did:key:zSpace) --delegates--> Alice (did:key:zAlice) --delegates--> Bob (did:key:zBob)

UCAN1: { iss: "did:key:zSpace", aud: "did:key:zAlice", att: [{can: "*", with: "did:key:zSpace"}] }
UCAN2: { iss: "did:key:zAlice", aud: "did:key:zBob", att: [{can: "store/add", with: "did:key:zSpace"}], prf: [CID(UCAN1)] }
```

### 4.2.3 Proof Verification Traversal

When a verifier receives an invocation, it must verify the entire delegation chain:

1. **Signature verification**: The UCAN's signature must be valid for the issuer's (`iss`) public key
2. **Audience check**: The outermost UCAN's `aud` must match the verifier's own DID
3. **Principal alignment**: For each proof in `prf`, the proof's `aud` must equal the current UCAN's `iss`
4. **Capability attenuation**: Each delegation may only delegate a subset (or equal set) of capabilities it received -- capabilities cannot be escalated
5. **Time bounds**: The UCAN must be within its `nbf` (not-before) and `exp` (expiration) bounds
6. **Revocation check**: The UCAN must not have been revoked
7. **Resource ownership**: The verifier must verify that the root of the chain actually owns the claimed resource

The traversal is recursive: starting from the invocation UCAN, walk each proof, verify it, then walk its proofs, until reaching a root UCAN with no proofs (self-asserted authority by the resource owner).

## 4.3 UCAN Revocation

### 4.3.1 Core UCAN Revocation Spec

**Source**: [UCAN Revocation Specification](https://ucan.xyz/revocation/)

Revocation invalidates a UCAN after the fact, beyond its built-in constraints (expiry, scope). Key principles:

- **Who can revoke**: Any issuer of a delegation in a proof chain may revoke that delegation. In a chain `Alice -> Bob -> Carol`, Alice can revoke any of the UCANs in the chain; Carol can only revoke the innermost.
- **Immutability**: Revocations are permanent and irreversible. Recipients treat them as a monotonically-growing set.
- **Delivery**: Revocation is accomplished by delivery of an unforgeable message from a previous delegator. UCAN revocations are similar to block lists.
- **Weak constraints**: Designed to work in eventually consistent contexts, with single sources of truth, or among consensus nodes.
- **Principle of least authority**: Certificate expiry and reduced capability scope should be the preferred method; revocation is a manual fallback.

### 4.3.2 Storacha ucan/revoke Extension

**Source**: `specs/w3-ucan.md`

Storacha extends the core UCAN revocation with a `ucan/revoke` capability:

```ipldsch
type Revoke struct {
  with    Authority   // DID of the principal that issued the UCAN being revoked or in its proof chain
  nb      Revocation
}

type Revocation struct {
  ucan    &UCAN       // link to the UCAN being revoked
  proof   &UCAN[]     // path from revoked UCAN to the authority's UCAN
}
```

**Key design decisions:**
- By making revocation a UCAN capability itself, the ability to revoke can be delegated to another principal (e.g., an auditor can revoke capabilities from misbehaving actors without being in the delegation chain)
- The `with` field MUST be the DID of the principal that issued the UCAN being revoked (or some UCAN in its proof chain)
- The `nb.proof` field is RECOMMENDED to contain UCAN links showing the path from the revoked UCAN to the authority
- Revocations are treated as permanent even if the enclosing UCAN has time bounds; the time bounds limit when the issuer can exercise the revocation ability, not the duration of the revocation itself

## 4.4 Storacha Authorization Flow (w3-session)

**Source**: `specs/w3-session.md`

### 4.4.1 Step-by-Step Authorization Flow

The flow uses an email-based authorization pattern with an Oracle intermediary:

**Roles:**
| Role | Description |
|------|-------------|
| Account | Principal identified by `did:mailto` (e.g., `did:mailto:web.mail:alice`) |
| Agent | Principal identified by `did:key`, representing a user's app/device |
| Oracle | Principal trusted by Authority to conduct out-of-band authorization |
| Authority | Principal representing the service provider (e.g., `did:web:web3.storage`) |
| Verifier | Component that performs UCAN validation |

**Step-by-step flow:**

1. **Agent sends `access/authorize` to Oracle (Authority)**:
   - `iss`: agent's `did:key`
   - `aud`: authority's `did:web`
   - `with`: agent's `did:key`
   - `nb.iss`: account's `did:mailto`
   - `nb.att`: array of requested capabilities (e.g., `[{"can": "store/*"}]`)

2. **Oracle sends confirmation email** to the account's email address (derived from `did:mailto`)

3. **User clicks confirmation link** in the email, which triggers `access/confirm` invocation

4. **Oracle issues delegation from account to agent**:
   - `iss`: `did:mailto:web.mail:alice` (the account)
   - `aud`: agent's `did:key`
   - `att`: the granted capabilities
   - Signed with attestation signature (empty bytes `gKADAA`)

5. **Oracle issues `ucan/attest` session proof**:
   - `iss`: `did:web:web3.storage` (the authority)
   - `aud`: agent's `did:key`
   - `can`: `ucan/attest`
   - `nb.proof`: CID link to the delegation from step 4

6. **Agent receives both the delegation and the attestation** (via polling `access/claim`)

7. **Agent can now invoke capabilities** using the delegation + attestation as proofs

### 4.4.2 Authorization Session (ucan/attest)

An authorization session is a UCAN delegation from the Authority to the Agent. It attests that the account holder authorized a specific delegation.

```ipldsch
type Session union {
  | Attest    "ucan/attest"
} representation inline {
  discriminantKey "can"
}

type Attest struct {
  with    Authority       // DID of the authority (e.g., did:web:web3.storage)
  nb      Attestation
}

type Attestation struct {
  proof   &UCAN           // link to the attested delegation
}
```

**Key rules:**
- Session MUST be issued by the authority or a trusted oracle
- Session audience MUST be the same principal as the audience of the attested proof
- The `with` field MUST be the authority's DID
- Sessions are subject to time bounds and revocations
- Sessions serve as verifiable cache records -- if provided, they enable optimized verification; if not, correct implementations fall back to full verification

### 4.4.3 Attestation Signature Mechanism

Since `did:mailto` has no private key, two signature types are defined:

**1. DKIM Signature:**
- The user sends an email from their account address with the authorization payload in the `Subject` header
- The DKIM signature of the email message is extracted and used as the UCAN signature
- Authorization payload format: `"I am signing ipfs://<CID> to grant access to this account"`
- Encoded as a Nonstandard VarSig with `alg` set to `"DKIM"`
- NOT currently supported in the w3up implementation

**2. Attestation Signature (current implementation):**
- A zero-byte signature placeholder: `{ "/": { "bytes": "gKADAA" } }`
- This signature alone is NOT valid -- it MUST be accompanied by a `ucan/attest` from the trusted authority
- The authority vouches for the delegation through the interactive email confirmation flow
- If a delegation with attestation signature is received without an accompanying attestation, the service MAY initiate an interactive verification flow retroactively

## 4.5 W3 Access Protocol

**Source**: `specs/w3-access.md`

### 4.5.1 access/delegate

Allows an authorized agent to send delegations to their respective audiences via the service as a message channel.

```ipldsch
type AccessDelegate struct {
  with   AgentDID          // did:key of the space where delegations are stored
  nb     Delegate
}

type Delegate struct {
  delegations { String: &UCAN }  // map of delegation links
}
```

- The `with` field is the space DID where delegations are stored
- The issuer of delegations need not be the same as the invocation issuer
- The service acts as a message channel -- like a mailbox for UCAN delegations
- All linked UCANs must be bundled with the invocation in the w3up implementation

### 4.5.2 access/claim

Allows an agent to receive delegations that were sent to them.

```ipldsch
type AccessClaim struct {
  with   DID   // DID of the audience of desired delegations
}
```

- Returns all delegations where the `with` DID is the audience
- Used by agents to poll for new delegations (e.g., after authorization flow completes)

### 4.5.3 access/request

Newer capability (replacing deprecated `access/authorize`) for requesting authorization from an account.

```ipldsch
type AccessRequest struct {
  can   { Ability: [Clause] }  // requested capabilities with optional constraints
}
```

- The `aud` field targets the account `did:mailto`
- Supports predicate-based constraints on requested capabilities (e.g., `{">": {"size": 1024}}`)

## 4.6 W3 Account Protocol

**Source**: `specs/w3-account.md`

### 4.6.1 Account Concept and Roles

An account is a principal identified by a memorable identifier such as `did:mailto`. It serves as:
- **Capability aggregator**: Spaces delegate full authority to an account for recovery and management
- **Access synchronizer**: All capabilities flow through the account, enabling multi-device access
- **Recovery mechanism**: Even if all devices are lost, as long as the user controls their email, the account can delegate capabilities to new agents

Key distinction: `did:key` identifiers can delegate capabilities natively via UCAN signatures. Accounts (`did:mailto`) bring human-meaningful identifiers and out-of-band authorization, freeing users from key management.

### 4.6.2 Signature Types for did:mailto

Two signature types defined for delegations issued by `did:mailto`:

**DKIM Signature (not yet implemented):**
- Email is sent from the account address with an authorization payload in the subject
- The DKIM signature proves the email owner authorized the delegation
- Encoded as `VarSig` with `alg: "DKIM"`

**Attestation Signature (current implementation):**
- Zero-byte placeholder signature: `{ "/": { "bytes": "gKADAA" } }`
- Must be accompanied by a `ucan/attest` from a trusted authority
- The authority confirms via interactive email flow that the account holder approved

### 4.6.3 Multi-Device Access Pattern

1. Alice installs the app on Device A, creates `did:key:zAgent1`
2. App asks for email, Alice enters `alice@web.mail`
3. App derives `did:mailto:web.mail:alice` as the account DID
4. App creates a new space `did:key:zSpace` and delegates `{ can: "*", with: "did:key:zSpace" }` to the account
5. App uses `access/delegate` to store the delegation with the service
6. On Device B, Alice installs the app, creates `did:key:zAgent2`
7. App invokes `access/authorize` requesting capabilities from `did:mailto:web.mail:alice`
8. Service sends confirmation email to Alice
9. Alice clicks the link, service issues delegation from account to `did:key:zAgent2` plus `ucan/attest`
10. Agent on Device B polls `access/claim` and receives the delegation + attestation
11. Device B now has access to Alice's space

---

# Topic 5: Content Claims and Indexing

## 5.1 Content Claims Protocol

**Source**: `content-claims/README.md`

Content claims are verifiable assertions about content-addressable data. They are UCAN capabilities in the `assert/` namespace. The production deployment is at `https://claims.web3.storage`.

### 5.1.1 Location Claim (assert/location)

Claims that a CID is available at a URL.

```js
{
  content: CID,           // CAR CID
  location: ['https://r2.cf/bag...car', 's3://bucket/bag...car'],
  range?: {               // optional byte range within the URL
    offset: number,
    length?: number
  }
}
```

- Issued by storage providers to indicate where content can be retrieved
- Part of the blob protocol's `blob/accept` receipt (as a location commitment)
- Can include multiple URLs for redundancy

### 5.1.2 Inclusion Claim (assert/inclusion)

Claims that a CID includes the contents described by another CID (typically a CARv2 index).

```js
{
  content: CID,           // CAR CID
  includes: CID,          // CARv2 Index CID
  proof?: CID             // optional zero-knowledge proof
}
```

- Used to assert that a CAR file contains certain blocks, as described by an index
- The index CID points to a CARv2 index structure

### 5.1.3 Index Claim (assert/index)

Claims that a content graph can be found in blobs identified and indexed by the given index CID.

```js
{
  content: CID,           // content root CID
  index: CID              // link to Content Archive containing the index
}
```

- Points to an `index/sharded/dag@0.1` structure
- This is the primary claim type for the new indexing system

### 5.1.4 Partition Claim (assert/partition)

Claims that a CID's graph can be read from blocks found in specified parts (CAR files).

```js
{
  content: CID,           // content root CID
  blocks?: CID,           // CIDs CID (optional list of block CIDs)
  parts: [CID, CID, ...] // CAR CIDs
}
```

- Indicates which CAR files contain the blocks of a content DAG
- Used for content that spans multiple shards

### 5.1.5 Equivalency Claim (assert/equals)

Claims that the same data is referred to by another CID or multihash.

```js
{
  content: CID,           // original CID
  equals: CID             // equivalent CID
}
```

- Example: mapping a CAR CID to its CommP (Piece CID) for Filecoin
- Enables cross-system identifier mapping

### 5.1.6 Relation Claim (assert/relation)

Claims that a CID links to other CIDs, combining aspects of partition and inclusion claims.

```js
{
  content: CID,                    // block CID
  children: [CID, CID, ...],      // linked block CIDs
  parts: [
    {
      content: CID,               // CAR CID
      includes?: {
        content: CID,             // CARv2 Index CID
        parts?: [CID, ...]        // where the index CID can be found
      }
    }
  ]
}
```

- Asserts that a block of content links to other blocks
- Specifies that the block and its links may be found in specified parts
- For each part, optionally includes an inline inclusion claim and a nested partition claim

### Content Claims HTTP API

```
GET /claims/multihash/:multihash    -- fetch claims by multihash (base58btc encoded)
GET /claims/cid/:cid                -- fetch claims by CID
```

Query parameter `?walk=parts,includes` allows traversing related claims.

Claims are stored as signed UCAN invocations in S3, indexed in DynamoDB by content multihash. The service is identified by `did:web:claims.web3.storage`.

## 5.2 IPNI (InterPlanetary Network Indexer)

**Source**: [IPNI Spec](https://github.com/ipni/specs/blob/main/IPNI.md), [IPFS Docs](https://docs.ipfs.tech/concepts/ipni/)

### 5.2.1 Overview and Architecture

IPNI is a content routing system optimized to take billions of CIDs from large data providers and provide fast lookup of provider information via a simple HTTP REST API.

It maps content identifiers (CIDs / multihashes) to **provider records** that tell you:
- Who has the data (provider identity)
- Where they are (multiaddresses)
- How to retrieve it (protocol metadata)

### 5.2.2 Advertisement Chain Structure

Advertisements form an immutable, authenticated linked list:
- Each advertisement is an IPLD DAG node
- Each advertisement links to the previous advertisement via a `PreviousID` field
- The chain is signed by the content provider's identity
- Advertisements are immutable once published

The chain represents a log of changes: "I now have these multihashes" or "I no longer have these multihashes."

### 5.2.3 Advertisement Schema Fields

Key fields in an advertisement:

| Field | Description |
|-------|-------------|
| `PreviousID` | Link to the previous advertisement in the chain |
| `Provider` | Peer ID of the content provider |
| `Addresses` | Multiaddresses where provider can be reached |
| `Entries` | Link to a chain of Entry Chunks containing multihashes |
| `ContextID` | Key identifying the content being advertised; used for updates/removal |
| `Metadata` | Opaque bytes describing how to retrieve data (starts with varint protocol ID) |
| `IsRm` | Boolean flag: `true` means this advertisement removes previously published content |
| `Signature` | Cryptographic signature over the serialized advertisement |
| `ExtendedProviders` | Optional: additional providers with their own addresses and metadata |

**Signing process:**
1. Serialize the full advertisement with Signature replaced by empty bytes
2. Hash the serialization
3. Sign the hash with the provider's private key

### 5.2.4 Entry Chunks and Multihash Lists

The content multihashes are stored in a linked list of Entry Chunks:

```
EntryChunk {
  Multihashes: [multihash, multihash, ...]   // batch of multihashes
  Next: Link<EntryChunk> | null               // link to next chunk
}
```

- Enables pagination for large sets of multihashes
- Each chunk contains a batch plus a link to the next chunk
- Chunks are linked via CIDs forming a traversable chain

### 5.2.5 Announcements

Announcements are transient notifications that signal changes to the advertisement chain:
- Contain the CID of the latest advertisement
- Include multiaddresses where the advertisement can be fetched
- Can be delivered via:
  - **Gossip pubsub** (libp2p gossipsub)
  - **HTTP** notification to known indexer endpoints

### 5.2.6 Provider Records and Lookups

**Lookup API:**
```
GET /cid/{cid}
GET /multihash/{multihash}
```

Returns a list of provider records:
```json
{
  "MultihashResults": [
    {
      "Multihash": "...",
      "ProviderResults": [
        {
          "ContextID": "...",
          "Metadata": "...",
          "Provider": {
            "ID": "peer-id",
            "Addrs": ["multiaddr1", "multiaddr2"]
          }
        }
      ]
    }
  ]
}
```

All IPNI HTTP requests use the URL path prefix `/ipni/v1/ad/`.

## 5.3 Sharded DAG Index

**Source**: `specs/w3-index.md`

### 5.3.1 Index Schema (index/sharded/dag@0.1)

The Sharded DAG Index is the core data structure that maps block CIDs to their physical locations within blobs. It is a versioned variant type:

```ts
type Index = Variant<{
  "index/sharded/dag@0.1": ShardedDAGIndex
}>
```

### 5.3.2 BlobIndex and BlobSlice Types

```ts
type ShardedDAGIndex = {
  content: Link<any>           // content root CID
  shards: Link<BlobIndex>[]    // links to blob indexes
}

type BlobIndex = [
  digest: Multihash,           // hash digest of the blob
  slices: BlobSlice[]          // index of blob slices
]

type BlobSlice = [
  digest: Multihash,           // hash digest of the slice (block CID)
  offset: Int,                 // byte offset within the blob
  length: Int                  // size in bytes
]
```

### 5.3.3 How CIDs Map to Byte Ranges in Blobs

The mapping works as follows:

1. A content DAG (e.g., a file) is split into multiple blobs (CAR shards)
2. Each blob contains multiple IPLD blocks at specific byte offsets
3. The `ShardedDAGIndex` records:
   - The `content` root CID of the DAG
   - For each blob (shard): the blob's multihash and a list of slices
   - For each slice: the block's multihash, its byte offset within the blob, and its length

**Example:**
```js
{
  "index/sharded/dag@0.1": {
    "content": { "/": "bafy..dag" },
    "shards": [
      link([
        { "/": { "bytes": "blb...left" } },   // blob multihash
        [
          [{ "/": { "bytes": "block..1"} }, 0, 128],     // block at offset 0, 128 bytes
          [{ "/": { "bytes": "block..2"} }, 129, 256],    // block at offset 129, 256 bytes
          [{ "/": { "bytes": "block..3"} }, 257, 384],
          [{ "/": { "bytes": "block..4"} }, 385, 512]
        ]
      ]),
      link([
        { "/": { "bytes": "blb...right" } },  // another blob
        [
          [{ "/": { "bytes": "block..5"} }, 0, 128],
          // ...
        ]
      ])
    ]
  }
}
```

To retrieve block `block..2`:
1. Look up the ShardedDAGIndex for the content
2. Find that `block..2` is in blob `blb...left` at offset 129, length 256
3. Use the location claim for `blb...left` to get its URL
4. Issue an HTTP range request for bytes 129-384

It is RECOMMENDED to include a BlobSlice spanning the full range of the blob. Shards can be linked externally or bundled inside the Content Archive of the Index.

## 5.4 W3 Blob Protocol

**Source**: `specs/w3-blob.md`

### 5.4.1 Blob Add Workflow

The `space/blob/add` capability stores a blob in a space. The workflow has three phases:

1. **Allocate** (`blob/allocate`): Service allocates memory for the blob and returns a presigned URL
   - Input: space DID, blob (digest + size), cause (link to add task)
   - Output: size allocated, optional address (URL + headers + expiry)
   - If blob already exists, size=0 and no address is returned

2. **Put** (`http/put`): Agent uploads the blob content via HTTP PUT
   - Subject is a derived `did:key` from the blob multihash
   - URL and headers come from allocation result (piped via `ucan/await`)
   - Private key is exposed in facts field so any agent can perform the upload

3. **Accept** (`blob/accept`): Service verifies the uploaded content
   - Blocks until content is delivered
   - Returns a `site` field containing a location commitment
   - If content doesn't match expected multihash/size, fails

### 5.4.2 Location Commitment

Produced as part of `blob/accept`, the location commitment is a signed assertion:

```ts
type LocationCommitment = {
  can: "assert/location"
  with: ProviderDID
  nb: {
    space: SpaceDID
    content: Multihash      // must match the blob
    url: string             // HTTP(S) URL where blob can be retrieved
    range?: {
      offset: int
      length?: int
    }
  }
}
```

This commitment is used by the content claims system to record where data lives.

## 5.5 W3 Index Protocol (space/index/add)

**Source**: `specs/w3-index.md`

The `space/index/add` capability submits a content index for publishing on IPNI.

```ts
type AddIndex = {
  cmd: "/space/index/add"
  sub: SpaceDID
  args: {
    index: Link<ContentArchive<Index>>  // CAR containing the Index
  }
}
```

- The index is wrapped in a Content Archive (CAR file) with the Index block as root
- The invocation SHOULD include a temporary delegation to the service allowing index retrieval
- After submission, the service publishes the index data to IPNI, making blocks publicly queryable

---

# Topic 6: Filecoin Pipeline

## 6.1 Filecoin Proofs Overview

**Sources**: [Filecoin Spec](https://spec.filecoin.io/), [Filecoin Docs - Proofs](https://docs.filecoin.io/basics/the-blockchain/proofs)

### 6.1.1 Proof of Replication (PoRep) and Sealing

PoRep proves that a storage provider has created a unique, sealed copy of the data:

1. **PreCommit (PC1 + PC2)**: Data is encoded through a slow, sequential process called sealing
   - The sealed version depends on the provider's identity and sector number
   - Uses Stacked DRG (Depth Robust Graph) encoding
   - Creates `CommR` (Commitment of Replication) -- the sealed sector's Merkle root
   - Also computes `CommD` (Commitment of Data) -- the unsealed sector's Merkle root (this is the aggregate piece commitment)

2. **Commit (C1 + C2)**: A zk-SNARK proof is generated proving the sealing was done correctly
   - Proves the relationship between `CommD` and `CommR`
   - Submitted on-chain

The sealing process is intentionally slow and sequential, making it infeasible for a dishonest prover to regenerate sealed sectors on demand.

### 6.1.2 Proof of Spacetime (PoSt)

PoSt proves that data continues to be stored over time. Two types:

**WinningPoSt:**
- Used in block consensus (leader election)
- A randomly selected SP must prove they have a replica at the specific time of selection
- Must respond within a short deadline (seconds)
- Failure means missing the block reward opportunity

**WindowPoSt:**
- Continuous audit of all SPs
- Storage providers have a 30-minute deadline to respond
- Proofs are zk-SNARKs submitted as blockchain messages
- Sectors are partitioned into "deadlines" -- each deadline is proven once per 24 hours
- Failure results in penalties (slashing)

### 6.1.3 Proof of Data Possession (PDP)

**Source**: [Filecoin PDP Blog](https://filecoin.io/blog/posts/introducing-proof-of-data-possession-pdp-verifiable-hot-storage-on-filecoin/), [PDP Docs](https://docs.filecoin.io/storage-providers/pdp)

PDP is a newer proof system for hot storage verification, live on mainnet:

- Proves that a storage provider holds an immediately available (unsealeded) copy of data
- Uses random sampling challenges: only 160 bytes per challenge regardless of dataset size
- Data remains in raw, accessible form (no sealing required)
- Proofs can be incrementally added, deleted, and modified (no aggregation bottlenecks)
- Designed for hot storage: retrieval services, dApp frontends, AI datasets
- PDP service contracts are deployed on Filecoin Mainnet and Calibration Testnet
- Complementary to PoRep/PoSt (which are for cold/sealed storage)

## 6.2 CommP (Piece Commitment) Computation

**Sources**: [Filecoin Spec - Piece](https://spec.filecoin.io/systems/filecoin_files/piece/), [go-fil-commp-hashhash](https://github.com/filecoin-project/go-fil-commp-hashhash)

### 6.2.1 FR32 Padding Algorithm

FR32 padding ensures data fits within the arithmetic field of the BLS12-381 curve (used in Filecoin's zk-SNARKs). The field element size is 254 bits but storage uses 32-byte (256-bit) chunks.

**Algorithm:**
- For every 254 bits of input data, insert 2 zero bits to make 256 bits
- This means every 31.75 bytes of input becomes 32 bytes of output
- More precisely: for each group of 32 bytes, the top 2 bits of each 32-byte chunk are forced to zero
- The expansion ratio is 256/254 (approximately 1.008x)

**Why FR32 exists:**
The name "Fr32" comes from the field element representation of BLS12-381. The field modulus is slightly less than 2^254, so only 254 bits of each 256-bit chunk can carry data. The 2 padding bits ensure each 32-byte chunk is a valid field element.

### 6.2.2 Power-of-Two Padding

After FR32 padding:
1. The FR32-padded data size is calculated
2. The next power-of-two size above the FR32-padded size is determined
3. The gap is filled with zero bytes

This ensures the data forms a complete, balanced binary Merkle tree.

### 6.2.3 Merkle Tree Construction and CommP

After both padding steps:
1. The padded data is split into 32-byte leaf nodes
2. A binary Merkle tree is constructed using SHA-256 (truncated to 254 bits) as the hash function
3. Each internal node is `SHA256-trunc254(left_child || right_child)`
4. The root of this tree is the **Piece Commitment (CommP)**, also known as the **Piece CID**

The Piece CID uses the multihash codec `fil-commitment-unsealed` and is typically encoded with multicodec prefix `0xf101`.

### 6.2.4 Piece Sizes and Alignment

- Piece sizes MUST be powers of two (after all padding)
- Minimum practical piece size: 128 bytes (padded)
- Standard sector sizes: 32 GiB, 64 GiB
- Pieces are padded to the next power of two before computing CommP
- Multiple pieces can be aggregated into a sector, each aligned to power-of-two boundaries

## 6.3 FRC-0058: Verifiable Data Aggregation

**Source**: [FRC-0058](https://github.com/filecoin-project/FIPs/blob/master/FRCs/frc-0058.md), [storacha/data-segment](https://github.com/storacha/data-segment)

### 6.3.1 Problem Statement

Small pieces of data undergo an aggregation process, combining them into a large deal for acceptance by a Storage Provider. Before FRC-0058, the aggregation was unverifiable:
- Users relied on the Aggregator to perform work correctly
- Impossible to prove to a third party that data was included in a deal
- No way to verify retrievability

### 6.3.2 Data Segments

A **Data Segment** is defined as:
- An array of bytes the client requested to be stored, after FR32 bit padding
- Identified by a commitment using the same algorithm as PieceCID (SHA-256-truncated, 2-ary Merkle tree)
- Data Segments MUST be aligned to the next power-of-two boundary
- Padding with NUL bytes up to the next power-of-two boundary

### 6.3.3 Aggregation Scheme

The aggregation process:

1. **Individual piece commitment**: Each client's data segment has its own CommP (Piece CID)
2. **Alignment**: Each data segment is padded to the next power-of-two size
3. **Concatenation**: Segments are concatenated in order
4. **Aggregate commitment**: A single CommP is computed over the entire concatenated, padded data
5. **Data Segment Index**: A special index is appended that maps each segment to its position

The aggregate is a single balanced binary Merkle tree where each data segment occupies a contiguous subtree.

### 6.3.4 Inclusion Proofs (DataAggregationProof)

The inclusion proof structure from the w3-filecoin spec:

```json
{
  "piece": "commitment...car",           // client's piece CID
  "aggregate": "commitment...aggregate",  // aggregate piece CID
  "inclusion": {
    "tree": {
      "path": ["bafk...root", "bafk...parent", "bafk...child", "bag...car"],
      "at": 1                             // position index
    },
    "index": {
      "path": ["..."],
      "at": 7                             // position in segment index
    }
  },
  "aux": {
    "dataType": 0,
    "dataSource": {
      "dealID": 1245                      // on-chain deal ID
    }
  }
}
```

The proof has two components:
- **`tree`**: A Merkle inclusion proof of the client's data sub-tree within the aggregate tree. The `path` contains the sibling hashes along the path from the client's subtree root to the aggregate root. The `at` field indicates the position.
- **`index`**: A Merkle inclusion proof of the data segment descriptor within the data segment index. This proves the position and size of the data within the aggregate.

The proof size for a 2-ary tree is: `sizeOfNode * (depthOfTree + 1)`. For 32-byte nodes and 30-layer trees: 992 bytes.

**What the proof guarantees:**
1. Client's data is included within the on-chain deal
2. Client's data can be trivially discovered within the deal for retrieval
3. Malicious behavior by the Aggregator or other users does not interfere with retrievability

### 6.3.5 Piece Multihash CID (fr32-sha2-256-trunc254-padded-binary-tree)

A newer multihash type that combines the root hash with tree metadata:

```
Digest = uvarint(padding) | uint8(height) | 32-byte-root
```

- `padding`: number of bytes needed to pad the underlying data such that after FR32 padding it forms a full binary tree
- `height`: the tree height
- `root`: the 32-byte Merkle root

This allows computing the actual data size from the multihash: `data_size = (2^height * 32 * 254/256) - padding`

## 6.4 W3 Filecoin Protocol (Storacha Pipeline)

**Source**: `specs/w3-filecoin.md`

### 6.4.1 Roles in the Pipeline

| Role | Description | Example DID |
|------|-------------|-------------|
| **Storefront** | Storage API facing users; receives pieces and tracks deals | `did:web:web3.storage` |
| **Aggregator** | Combines small pieces into large aggregates per FRC-0058 | `did:web:aggregator.web3.storage` |
| **Dealer** | Arranges Filecoin deals with Storage Providers | `did:web:dealer.web3.storage` |
| **Deal Tracker** | Follows the Filecoin chain to track deal status | `did:web:tracker.web3.storage` |

### 6.4.2 Pipeline Flow Step by Step

The complete flow from user upload to Filecoin deal:

**Phase 1: Piece Submission (Storefront)**

1. User (or trusted actor) computes the Piece CID (CommP) for their content
2. Agent invokes `filecoin/offer` on the Storefront with `{content: CID, piece: PieceCID}`
3. Storefront acknowledges with receipt containing:
   - `fx.join` -> `filecoin/accept` (final result shortcut)
   - `fx.fork` -> `filecoin/submit` (next step in chain)

4. Storefront verifies the piece, then issues `filecoin/submit` receipt with:
   - `fx.join` -> `piece/offer` (forwarding to Aggregator)

**Phase 2: Aggregation (Aggregator)**

5. Storefront invokes `piece/offer` on the Aggregator with `{piece: PieceCID, group: "did:web:free.web3.storage"}`
6. Aggregator queues the piece and acknowledges with receipt containing:
   - `fx.join` -> `piece/accept` (will succeed with inclusion proof or fail)

7. When the Aggregator has enough pieces to build a qualified aggregate, it includes the piece and issues `piece/accept` receipt with:
   - Result: `{piece, aggregate, inclusion}` (the inclusion proof)
   - `fx.join` -> `aggregate/offer`

**Phase 3: Deal Making (Dealer)**

8. Aggregator invokes `aggregate/offer` on the Dealer with `{aggregate: PieceCID, pieces: Link<[PieceCID]>}`
   - The `pieces` field links to a DAG-CBOR encoded list of piece CIDs in the same order they were aggregated
9. Dealer acknowledges and begins deal negotiation with Filecoin Storage Providers (out of band)
10. Dealer issues `aggregate/accept` receipt:
    - On success: `{aggregate, dataType: 0, dataSource: {dealID: N}}`
    - On failure with recoverable pieces: fork effects with `piece/offer` tasks for retry

**Phase 4: Deal Tracking**

11. Storefront (or anyone) can invoke `deal/info` on the Deal Tracker to query deal status
12. Deal Tracker returns deal information from the Filecoin chain:
    ```json
    {
      "deals": {
        "111": {
          "storageProvider": "f07...",
          "status": "Active",
          "activation": "2023-04-13T01:58:00+00:00",
          "expiration": "2024-09-05T01:58:00+00:00"
        }
      }
    }
    ```

### 6.4.3 Storefront Capabilities

| Capability | Description |
|-----------|-------------|
| `filecoin/offer` | User submits a piece for Filecoin storage. Returns pending acknowledgment. |
| `filecoin/submit` | Internal: Storefront verifies piece and queues for aggregation. |
| `filecoin/accept` | Terminal: resolves when piece is in a live Filecoin deal. Returns DataAggregationProof. |
| `filecoin/info` | Query: returns known information about a piece (aggregates, deals, inclusion proofs). |

Schema for `filecoin/offer`:
```ipldsch
type FilecoinOfferDetail struct {
  content &Content         // CID of uploaded content
  piece   PieceLink        // CommP piece CID
}
```

### 6.4.4 Aggregator Capabilities

| Capability | Description |
|-----------|-------------|
| `piece/offer` | Storefront offers a piece for aggregation. Includes a `group` field for aggregate grouping. |
| `piece/accept` | Issued when piece is included in an aggregate. Returns inclusion proof. |

Schema for `piece/offer`:
```ipldsch
type PieceOfferDetail struct {
  piece   PieceLink        // CommP piece CID
  group   string           // grouping key (subset of space)
}
```

Deduplication rules:
- Same piece from the same Storefront: considered duplicate, returns same receipt
- Same piece from different Storefronts: NOT considered duplicate
- Nonce can force re-inclusion in another aggregate

### 6.4.5 Dealer Capabilities

| Capability | Description |
|-----------|-------------|
| `aggregate/offer` | Aggregator offers a complete aggregate for deal-making. |
| `aggregate/accept` | Terminal: resolves when deals are live on Filecoin chain. |

Schema for `aggregate/offer`:
```ipldsch
type AggregateOfferDetail struct {
  pieces    &AggregatePieces   // link to DAG-CBOR list of piece CIDs
  aggregate PieceLink          // aggregate piece CID
}
```

The `pieces` list MUST be sorted in the same order as used to compute the aggregate piece CID.

### 6.4.6 Deal Tracker Capabilities

| Capability | Description |
|-----------|-------------|
| `deal/info` | Query deal status for an aggregate. Returns deal information from chain. |

Schema:
```ipldsch
type DealInfoDetail struct {
  aggregate PieceLink          // aggregate piece CID to look up
}
```

The invoker SHOULD use a nonce on subsequent calls to avoid receiving cached responses.

### 6.4.7 Inclusion Proof Structure

The `InclusionProof` returned by `piece/accept` has two parts:

```json
{
  "tree": {
    "path": ["bafk...", "bafk...", ...],   // Merkle siblings from piece subtree to aggregate root
    "at": 4                                 // position of piece in aggregate
  },
  "index": {
    "path": ["bafk...", ...],              // Merkle siblings in segment index
    "at": 7                                 // position in segment index
  }
}
```

The `DataAggregationProof` (from `filecoin/accept` and `aggregate/accept`) extends this:

```json
{
  "piece": "commitment...car",
  "aggregate": "commitment...aggregate",
  "inclusion": { ... },                    // InclusionProof as above
  "aux": {
    "dataType": 0,                         // 0 = standard deal
    "dataSource": {
      "dealID": 1245                       // on-chain deal ID
    }
  }
}
```

This structure provides end-to-end verifiability: from the user's original piece through aggregation to the on-chain Filecoin deal.

---

## Key Sources

### UCAN and DID Specifications
- [did:key Method v0.9](https://w3c-ccg.github.io/did-key-spec/)
- [did:web Method Specification](https://w3c-ccg.github.io/did-method-web/)
- [UCAN Specification](https://github.com/ucan-wg/spec) / [ucan.xyz/specification](https://ucan.xyz/specification/)
- [UCAN Delegation Spec](https://github.com/ucan-wg/delegation)
- [UCAN Revocation Specification](https://ucan.xyz/revocation/)

### Storacha Local Specs
- `specs/w3-session.md` -- Authorization protocol
- `specs/w3-access.md` -- Access delegation/claim protocol
- `specs/w3-account.md` -- Account and signature types
- `specs/w3-ucan.md` -- UCAN extensions (attest, revoke, conclude)
- `specs/did-mailto.md` -- did:mailto method
- `specs/w3-blob.md` -- Blob storage protocol
- `specs/w3-index.md` -- Sharded DAG indexing
- `specs/w3-filecoin.md` -- Filecoin pipeline protocol
- `content-claims/README.md` -- Content claims implementation

### IPNI and Filecoin Specifications
- [IPNI Specification](https://github.com/ipni/specs/blob/main/IPNI.md)
- [IPNI IPFS Docs](https://docs.ipfs.tech/concepts/ipni/)
- [FRC-0058: Verifiable Data Aggregation](https://github.com/filecoin-project/FIPs/blob/master/FRCs/frc-0058.md)
- [Filecoin Spec - Piece](https://spec.filecoin.io/systems/filecoin_files/piece/)
- [Filecoin Docs - Proofs](https://docs.filecoin.io/basics/the-blockchain/proofs)
- [Filecoin PDP](https://docs.filecoin.io/storage-providers/pdp)
- [storacha/data-segment](https://github.com/storacha/data-segment) -- FRC-0058 implementation
