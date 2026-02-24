# Research: Topics 4-6 Code Discovery

## Topic 4: UCAN Auth Model

### 4.1 Delegation Creation

**Key file:** `w3up/packages/access-client/src/space.js`

Spaces (the core resource) are `did:key` identities backed by Ed25519 keys. Creating a delegation from a space means signing a UCAN with the space's private key:

```js
// space.js lines 92-109
export const createAuthorization = async (
  { signer, name },
  {
    audience,
    access = Access.spaceAccess,
    expiration = UCAN.now() + SESSION_LIFETIME,
  }
) => {
  return await delegate({
    issuer: signer,
    audience: audience,
    capabilities: toCapabilities({
      [signer.did()]: access,
    }),
    ...(expiration ? { expiration } : {}),
    facts: [{ space: { name } }],
  })
}
```

**Key file:** `w3up/packages/access-client/src/agent.js`

The Agent's `delegate()` method creates delegations for the currently selected space:

```js
// agent.js lines 427-465
async delegate(options) {
    const space = this.currentSpaceWithMeta()
    if (!space) {
      throw new Error('no space selected.')
    }
    const caps = options.abilities.map((a) => ({
      with: space.did,
      can: a,
    }))
    // Verify agent can provide proofs for each requested capability
    for (const cap of caps) {
      if (!this.proofs([cap]).length) {
        throw new Error(`cannot delegate capability ${cap.can} with ${cap.with}`)
      }
    }
    const delegation = await delegate({
      issuer: this.issuer,
      capabilities: caps,
      proofs: this.proofs(caps),
      facts: [{ space: space.meta ?? {} }],
      ...options,
    })
    await this.#data.addDelegation(delegation, { audience: options.audienceMeta })
    return delegation
}
```

### 4.2 The `access/authorize` Flow (Email-based Authorization)

**Key file:** `w3up/packages/capabilities/src/access.js`

The `access/authorize` capability defines the email authorization request:

```js
// access.js lines 65-80
export const authorize = capability({
  can: 'access/authorize',
  with: DID.match({ method: 'key' }),
  nb: AuthorizationRequest,
  derives: (child, parent) => {
    return (
      and(equalWith(child, parent)) ||
      and(equal(child.nb.iss, parent.nb.iss, 'iss')) ||
      and(subsetCapabilities(child.nb.att, parent.nb.att)) ||
      ok({})
    )
  },
})
```

The `access/confirm` capability completes the flow when user clicks the email link:

```js
// access.js lines 88-111
export const confirm = capability({
  can: 'access/confirm',
  with: DID,
  nb: Schema.struct({
    cause: Schema.link({ version: 1 }),
    iss: Account,
    aud: Schema.did(),
    att: CapabilityRequest.array(),
  }),
  // ... derives checks
})
```

The `access/claim` capability retrieves delegations stored for a principal:

```js
// access.js lines 113-116
export const claim = capability({
  can: 'access/claim',
  with: DID.match({ method: 'key' }).or(DID.match({ method: 'mailto' })),
})
```

**Key file:** `w3up/packages/access-client/src/agent-use-cases.js`

The complete client-side authorization flow:

```js
// agent-use-cases.js lines 176-199
export async function authorizeAndWait(access, email, opts = {}) {
  const expectAuthorization = opts.expectAuthorization || waitForAuthorizationByPolling
  const account = { did: () => DidMailto.fromEmail(email) }
  await requestAccess(access, account, opts?.capabilities || [
    { can: 'space/*' },
    { can: 'store/*' },
    { can: 'provider/add' },
    { can: 'subscription/list' },
    { can: 'upload/*' },
    { can: 'ucan/*' },
    { can: 'plan/*' },
    { can: 'usage/*' },
    { can: 'w3up/*' },
  ])
  const sessionDelegations = [...(await expectAuthorization(access, opts))]
  if (!opts?.dontAddProofs) {
    await Promise.all(sessionDelegations.map(async (d) => access.addProof(d)))
  }
}
```

### 4.3 Session Tokens / Attestation (ucan/attest)

**Key file:** `w3up/packages/capabilities/src/ucan.js`

The `ucan/attest` capability is the attestation mechanism - issued by the service to vouch for a delegation:

```js
// ucan.js lines 130-143
export const attest = capability({
  can: 'ucan/attest',
  with: Schema.did(),     // Should be web3.storage DID
  nb: Schema.struct({
    proof: Schema.link({ version: 1 }),  // UCAN delegation being attested
  }),
  derives: (claim, from) =>
    and(equalWith(claim, from)) ??
    checkLink(claim.nb.proof, from.nb.proof, 'nb.proof'),
})
```

**Key file:** `w3up/packages/upload-api/src/access/confirm.js`

Session proofs are created as a pair: delegation + attestation:

```js
// confirm.js lines 106-137
export async function createSessionProofs({
  service, account, agent, facts, capabilities, delegationProofs, expiration = Infinity,
}) {
  // Create a delegation on behalf of the account with an absent signature.
  const delegation = await Provider.delegate({
    issuer: Absentee.from({ id: account.did() }),
    audience: agent,
    capabilities,
    expiration,
    proofs: delegationProofs,
    facts,
  })

  const attestation = await UCAN.attest.delegate({
    issuer: service,
    audience: agent,
    with: service.did(),
    nb: { proof: delegation.cid },
    expiration,
    facts,
  })

  return [delegation, attestation]
}
```

The account (`did:mailto`) creates a delegation with an **absent signature** (it has no private key), and the **service attests** that delegation by issuing `ucan/attest` referencing its CID.

### 4.4 `access/claim` - Proof Chain Validation

**Key file:** `w3up/packages/upload-api/src/access/claim.js`

The claim handler looks up stored delegations and validates attestations:

```js
// claim.js lines 45-120
export const claim = async ({ invocation }, { delegationsStorage, signer }) => {
  const claimedAudience = invocation.capabilities[0].with
  const storedDelegationsResult = await delegationsStorage.find({
    audience: claimedAudience,
  })
  // ...
  // Find any attested ucan:* delegations and replace them with fresh ones.
  for (const delegation of storedDelegationsResult.ok) {
    const attestCap = delegation.capabilities.find(isUCANAttest)
    if (!(attestCap && attestCap.with === signer.did())) continue

    // Validate: signature, not too early, not expired
    const valid =
      (await UCAN.verifySignature(delegation.data, signer)) &&
      !UCAN.isTooEarly(delegation.data) &&
      !UCAN.isExpired(delegation.data)
    if (!valid) continue
    // ... creates fresh session proofs from attested delegation
  }
}
```

### 4.5 did:mailto Usage

**Key file:** `w3up/packages/did-mailto/src/index.js`

The `did:mailto` DID method maps email addresses to DIDs:

```js
// index.js lines 9-27
export function fromEmail(email) {
  const { domain, local } = parseEmail(email)
  const did = `did:mailto:${encodeURIComponent(domain)}:${encodeURIComponent(local)}`
  return did
}

export function toEmail(did) {
  const parts = did.split(':')
  if (parts[1] !== 'mailto') {
    throw new Error(`DID ${did} is not a mailto did.`)
  }
  return `${decodeURIComponent(parts[3])}@${decodeURIComponent(parts[2])}`
}
```

Account DID schema in capabilities:

```js
// access.js line 25
export const Account = DID.match({ method: 'mailto' })
```

### 4.6 Revocation (ucan/revoke)

**Key file:** `w3up/packages/capabilities/src/ucan.js`

The `ucan/revoke` capability definition:

```js
// ucan.js lines 36-75
export const revoke = capability({
  can: 'ucan/revoke',
  with: Schema.did(),  // DID of principal authorizing revocation
  nb: Schema.struct({
    ucan: UCANLink,    // UCAN being revoked
    proof: UCANLink.array().optional(),  // Proof chain
  }),
  derives: (claim, from) =>
    and(equalWith(claim, from)) ??
    and(checkLink(claim.nb.ucan, from.nb.ucan, 'nb.ucan')) ??
    equal((claim.nb.proof ?? []).join('/'), (from.nb.proof ?? []).join('/'), 'nb.proof'),
})
```

**Key file:** `w3up/packages/upload-api/src/ucan/revoke.js`

The revoke handler resolves UCANs and stores revocations:

```js
// revoke.js lines 9-45
export const ucanRevokeProvider = ({ revocationsStorage }) =>
  provide(revoke, async ({ capability, invocation }) => {
    const resolveResult = resolve({ capability, blocks: invocation.blocks })
    if (resolveResult.error) return resolveResult
    const { ucan, principal } = resolveResult.ok
    const result =
      isParticipant(ucan, principal)
        ? await revocationsStorage.reset({
            revoke: ucan.cid, scope: principal, cause: invocation.cid,
          })
        : await revocationsStorage.add({
            revoke: ucan.cid, scope: principal, cause: invocation.cid,
          })
    return result.error
      ? { error: { name: 'RevocationsStoreFailure', message: result.error.message } }
      : { ok: { time: Date.now() } }
  })
```

**Key file:** `w3up/packages/upload-api/src/utils/revocation.js`

Authorization validation checks revocations against the full proof chain:

```js
// revocation.js lines 20-45
export const validateAuthorization = async ({ revocationsStorage }, auth) => {
  const query = toRevocationQuery(auth)
  const match = await revocationsStorage.query(query)
  if (match.error) return { error: new Revoked(auth.delegation) }
  for (const [ucan, scope = {}] of Object.entries(match.ok)) {
    for (const principal of Object.keys(scope)) {
      const delegation = query[ucan]?.[principal]
      if (delegation) return { error: new Revoked(delegation) }
    }
  }
  return { ok: {} }
}
```

### 4.7 Space Creation and Management

**Key file:** `w3up/packages/access-client/src/space.js`

Space generation creates an Ed25519 keypair (the `did:key`):

```js
// space.js lines 25-29
export const generate = async ({ name, agent }) => {
  const { signer } = await ED25519.generate()
  return new OwnedSpace({ signer, name, agent })
}
```

Recovery is a delegation to a `did:mailto` account:

```js
// space.js lines 68-73
export const createRecovery = (space, account) =>
  createAuthorization(space, {
    audience: DID.parse(account),
    access: Access.accountAccess,
    expiration: Infinity,
  })
```

**Key file:** `w3up/packages/w3up-client/src/client.js`

The high-level `createSpace()` method provisions the account, saves, and creates recovery:

```js
// client.js lines 275-308
async createSpace(name, options) {
    const space = await this._agent.createSpace(name)
    const account = options?.account
    if (account) {
      const provisionResult = await account.provision(space.did())
      if (provisionResult.error) throw new Error(...)
      await space.save()
      const recovery = await space.createRecovery(account.did())
      const delegationResult = await this.capability.access.delegate({
        space: space.did(),
        delegations: [recovery],
      })
      // ...
    }
    // Authorize Gateway Services
    // ...
}
```

**Key file:** `w3up/packages/capabilities/src/space.js`

Space capability definitions:

```js
// space.js lines 22-26
export const space = capability({
  can: 'space/*',
  with: SpaceDID,
  derives: equalWith,
})
```

---

## Topic 5: Content Claims & Indexing

### 5.1 Claim Type Definitions

**Key file:** `content-claims/packages/core/src/capability/assert.js`

All six claim types are defined here:

**assert/location** - Claims a CID is available at a URL:
```js
// assert.js lines 14-36
export const location = capability({
  can: 'assert/location',
  with: URI.match({ protocol: 'did:' }),
  nb: Schema.struct({
    content: linkOrDigest(),
    location: Schema.array(URI),
    range: Schema.struct({
      offset: Schema.integer(),
      length: Schema.integer().optional()
    }).optional(),
    space: Schema.principal().optional()
  }),
  // ... derives
})
```

**assert/index** - Claims a content graph can be found in blobs identified in an index:
```js
// assert.js lines 57-76
export const index = capability({
  can: 'assert/index',
  with: URI.match({ protocol: 'did:' }),
  nb: Schema.struct({
    content: linkOrDigest(),
    index: Schema.link({ version: 1 })
  }),
  // ... derives
})
```

**assert/inclusion** - Claims a CID includes contents claimed in another CID:
```js
// assert.js lines 41-51
export const inclusion = capability({
  can: 'assert/inclusion',
  with: URI.match({ protocol: 'did:' }),
  nb: Schema.struct({
    content: linkOrDigest(),
    includes: Schema.link({ version: 1 }),
    proof: Schema.link({ version: 1 }).optional()
  })
})
```

**assert/partition** - Claims a CID's graph can be read from parts:
```js
// assert.js lines 81-91
export const partition = capability({
  can: 'assert/partition',
  with: URI.match({ protocol: 'did:' }),
  nb: Schema.struct({
    content: linkOrDigest(),
    blocks: Schema.link({ version: 1 }).optional(),
    parts: Schema.array(Schema.link({ version: 1 }))
  })
})
```

**assert/relation** - Claims a CID links to other CIDs:
```js
// assert.js lines 96-114
export const relation = capability({
  can: 'assert/relation',
  with: URI.match({ protocol: 'did:' }),
  nb: Schema.struct({
    content: linkOrDigest(),
    children: Schema.array(Schema.link()),
    parts: Schema.array(Schema.struct({
      content: Schema.link({ version: 1 }),
      includes: Schema.struct({
        content: Schema.link({ version: 1 }),
        parts: Schema.array(Schema.link({ version: 1 })).optional()
      }).optional()
    }))
  })
})
```

**assert/equals** - Claims data is referred to by another CID/multihash:
```js
// assert.js lines 119-132
export const equals = capability({
  can: 'assert/equals',
  with: URI.match({ protocol: 'did:' }),
  nb: Schema.struct({
    content: linkOrDigest(),
    equals: Schema.link()
  }),
  // ... derives
})
```

### 5.2 Claim Publication (Server-Side)

**Key file:** `content-claims/packages/core/src/server/service/assert.js`

The content-claims service handler stores claims as archived invocations:

```js
// assert.js lines 9-42
export function createService(context) {
  return {
    inclusion: Server.provide(Assert.inclusion, input => handler(input, context)),
    index: Server.provide(Assert.index, input => handler(input, context)),
    location: Server.provide(Assert.location, input => handler(input, context)),
    partition: Server.provide(Assert.partition, input => handler(input, context)),
    relation: Server.provide(Assert.relation, input => handler(input, context)),
    equals: Server.provide(Assert.equals, input => handler(input, context))
  }
}

export const handler = async ({ capability, invocation }, { claimStore }) => {
  const { content } = capability.nb
  const archive = await invocation.archive()
  if (archive.error) throw new Error('failed invocation archive', { cause: archive.error })
  const claim = {
    claim: invocation.cid,
    bytes: archive.ok,
    content: 'digest' in content ? Digest.decode(content.digest) : content.multihash,
    expiration: invocation.expiration,
    value: capability
  }
  await claimStore.put(claim)
  return { ok: {} }
}
```

### 5.3 Content Claims Client (Reading Claims)

**Key file:** `content-claims/packages/core/src/client/index.js`

Claims are read via HTTP, streaming CAR blocks:

```js
// client/index.js lines 87-129
export const fetch = async (content, options) => {
  const path = `/claims/multihash/${base58btc.encode(content.bytes)}`
  const url = new URL(path, options?.serviceURL ?? serviceURL)
  if (options?.walk) url.searchParams.set('walk', options.walk.join(','))
  return globalThis.fetch(url)
}

export const read = async (content, options) => {
  const res = await fetch(content, options)
  if (!res.ok) throw new Error(...)
  const claims = []
  await res.body
    .pipeThrough(new CARReaderStream())
    .pipeTo(new WritableStream({
      async write(block) {
        const digest = await sha256.digest(block.bytes)
        if (!equals(block.cid.multihash.bytes, digest.bytes)) {
          throw new Error(`hash verification failed: ${block.cid}`)
        }
        const claim = await decode(block.bytes)
        claims.push(claim)
      }
    }))
  return claims
}
```

### 5.4 Sharded DAG Index

**Key file:** `w3up/packages/blob-index/src/sharded-dag-index.js`

The `index/sharded/dag@0.1` format maps DAG content to shard locations:

```js
// sharded-dag-index.js lines 10-19
export const version = 'index/sharded/dag@0.1'

export const ShardedDAGIndexSchema = Schema.variant({
  [version]: Schema.struct({
    content: Schema.link(),         // DAG root
    shards: Schema.array(Schema.link()),  // Shard links
  }),
})
```

The `ShardedDAGIndex` class maps shard digests to per-shard indexes (DigestMaps of slice digests to [offset, length]):

```js
// sharded-dag-index.js lines 88-125
class ShardedDAGIndex {
  constructor(content) {
    this.#content = content
    this.#shards = new DigestMap()   // Map<ShardDigest, DigestMap<SliceDigest, [offset, length]>>
  }
  setSlice(shard, slice, pos) {
    let index = this.#shards.get(shard)
    if (!index) {
      index = new DigestMap()
      this.#shards.set(shard, index)
    }
    index.set(slice, pos)
  }
  archive() { return archive(this) }
}
```

Archiving produces a CAR file with CBOR-encoded blocks:

```js
// sharded-dag-index.js lines 167-190
export const archive = async (model) => {
  const blocks = new Map()
  const shards = [...model.shards.entries()].sort(...)
  const index = { content: model.content, shards: [] }
  for (const s of shards) {
    const slices = [...s[1].entries()].sort(...)
      .map((e) => [e[0].bytes, e[1]])
    const bytes = dagCBOR.encode([s[0].bytes, slices])
    const digest = await sha256.digest(bytes)
    const cid = Link.create(dagCBOR.code, digest)
    blocks.set(cid.toString(), { cid, bytes })
    index.shards.push(cid)
  }
  const bytes = dagCBOR.encode({ [version]: index })
  const digest = await sha256.digest(bytes)
  const cid = Link.create(dagCBOR.code, digest)
  return ok(CAR.encode({ roots: [{ cid, bytes }], blocks }))
}
```

### 5.5 IPNI Publishing (via index/add handler)

**Key file:** `w3up/packages/upload-api/src/index/add.js`

The `index/add` handler publishes to IPNI and creates content claims:

```js
// index/add.js lines 21-80
const add = async ({ capability }, context) => {
  const space = capability.with
  const idxLink = capability.nb.index

  // Ensure the index was stored in the agent's space
  const idxAllocRes = await assertAllocated(context, space, idxLink.multihash, 'IndexNotFound')
  if (!idxAllocRes.ok) return idxAllocRes

  // Fetch the index from the network
  const idxBlobRes = await context.blobRetriever.stream(idxLink.multihash)
  // ... extract ShardedDAGIndex ...
  const idxRes = ShardedDAGIndex.extract(concat(chunks))

  // Ensure indexed shards are allocated in the agent's space
  const shardDigests = [...idxRes.ok.shards.keys()]
  // ... verify all shards allocated ...

  const publishRes = await Promise.all([
    // Publish the index data to IPNI
    context.ipniService.publish(idxRes.ok),
    // Publish a content claim for the index
    publishIndexClaim(context, { content: idxRes.ok.content, index: idxLink }),
  ])
  return ok({})
}
```

**Key file:** `ipni-publisher/pkg/publisher/publisher.go`

The Go IPNI publisher creates and signs IPNI advertisements:

```go
// publisher.go lines 26-48
type Publisher interface {
    Publish(ctx context.Context, provider peer.AddrInfo, contextID string,
        digests iter.Seq[mh.Multihash], meta metadata.Metadata) (ipld.Link, error)
}

func (p *IPNIPublisher) Publish(ctx context.Context, providerInfo peer.AddrInfo,
    contextID string, digests iter.Seq[mh.Multihash], meta metadata.Metadata) (ipld.Link, error) {
    link, err := p.publishAdvForIndex(ctx, providerInfo.ID, providerInfo.Addrs,
        []byte(contextID), meta, false, digests)
    if err != nil { return nil, fmt.Errorf("publishing IPNI advert: %w", err) }
    return link, nil
}
```

### 5.6 Indexing Service Query Handling (Go)

**Key file:** `indexing-service/pkg/service/service.go`

The `IndexingService.Query()` walks a graph of multihash lookups:

```go
// service.go lines 319-346
func (is *IndexingService) Query(ctx context.Context, q types.Query) (types.QueryResult, error) {
    initialJobs := make([]job, 0, len(q.Hashes))
    for _, mh := range q.Hashes {
        initialJobs = append(initialJobs, job{mh, nil, nil, q.Type})
    }
    qs, err := is.jobWalker(ctx, initialJobs, queryState{
        q: &q,
        qr: &queryResult{
            Claims:  make(map[cid.Cid]delegation.Delegation),
            Indexes: bytemap.NewByteMap[types.EncodedContextID, blobindex.ShardedDagIndexView](-1),
        },
        visits: map[jobKey]struct{}{},
    }, is.jobHandler)
    // ...
    return queryresult.Build(qs.qr.Claims, qs.qr.Indexes)
}
```

The query follows a chain: multihash -> IPNI provider records -> claim fetching -> claim-type-specific handling:

- **EqualsClaimMetadata**: follows to query the OTHER side of the equivalence
- **IndexClaimMetadata**: fetches the index CID's location, then fetches ShardedDagIndex
- **LocationCommitmentMetadata**: stores location claim; if for an index, fetches the full index blob and adds location queries for shards containing the target multihash

The `Publish()` method dispatches by claim type:

```go
// service.go lines 519-537
func Publish(ctx context.Context, id ucan.Signer, blobIndex blobindexlookup.BlobIndexLookup,
    claims contentclaims.Service, provIndex providerindex.ProviderIndex,
    provider peer.AddrInfo, claim delegation.Delegation) error {
    switch caps[0].Can() {
    case assert.EqualsAbility:
        return publishEqualsClaim(ctx, claims, provIndex, provider, claim)
    case assert.IndexAbility:
        return publishIndexClaim(ctx, id, blobIndex, claims, provIndex, provider, claim)
    default:
        return ErrUnrecognizedClaim
    }
}
```

---

## Topic 6: Filecoin Pipeline

### 6.1 PieceLink Type (CommP Commitment)

**Key file:** `w3up/packages/capabilities/src/filecoin/lib.js`

The PieceLink uses the `fr32-sha2-256-trunc254-padded-binary-tree` multihash codec:

```js
// lib.js lines 1-20
const FR32_SHA2_256_TRUNC254_PADDED_BINARY_TREE = 0x1011
const RAW_CODE = 0x55

export const PieceLink = Schema.link({
  code: RAW_CODE,
  version: 1,
  multihash: {
    code: FR32_SHA2_256_TRUNC254_PADDED_BINARY_TREE,
  },
})
```

### 6.2 CommP / Piece Computation

**Key file:** `data-segment/src/piece.js`

Piece commitment from payload:

```js
// piece.js lines 73-76
export const fromPayload = (payload) => fromDigest(digest(payload))
```

**Key file:** `data-segment/src/multihash.js`

The streaming hasher builds a Merkle tree while processing data:

```js
// multihash.js lines 22-30
export const name = 'fr32-sha2-256-trunc254-padded-binary-tree'
export const code = 0x1011

// Digest includes: [padding_varint, height_byte, 32_byte_root]
export const digest = (payload) => {
  const hasher = new Hasher()
  hasher.write(payload)
  return hasher.digest()
}
```

**Key file:** `fr32-sha2-256-trunc254-padded-binary-tree-multihash/src/hasher.rs`

The Rust/WASM implementation for high-performance CommP calculation:

```rust
// hasher.rs lines 42-49
pub struct PieceHasher {
    pub(crate) bytes_written: u64,
    buffer: QuadBuffer,
    offset: usize,
    layers: Layers,
    digest: [u8; MAX_MULTIHASH_SIZE],
}
```

### 6.3 FR32 Padding

**Key file:** `data-segment/src/fr32.js`

FR32 padding inserts 2 zero bits every 254 bits:

```js
// fr32.js lines 49-96
export const pad = (source, output = new Uint8Array(toPieceSize(source.length))) => {
  const size = toZeroPaddedSize(source.byteLength)
  const quadCount = size / IN_BYTES_PER_QUAD

  // Cycle over four(4) 31-byte groups, leaving 1 byte in between:
  // 31 + 1 + 31 + 1 + 31 + 1 + 31 = 127
  for (let n = 0; n < quadCount; n++) {
    const readOffset = n * IN_BYTES_PER_QUAD
    const writeOffset = n * OUT_BYTES_PER_QUAD

    output.set(source.subarray(readOffset, readOffset + 32), writeOffset)
    output[writeOffset + 31] &= 0b00111111  // first 2-bit shim

    for (let i = 32; i < 64; i++) {
      output[writeOffset + i] =
        (source[readOffset + i] << 2) | (source[readOffset + i - 1] >> 6)
    }
    output[writeOffset + 63] &= 0b00111111  // second 2-bit shim
    // ... continues for 4 groups
  }
  return output
}
```

Zero-padding calculation to fill a power-of-2 piece:

```js
// fr32.js lines 17-25
export function toZeroPaddedSize(payloadSize) {
  const size = Math.max(payloadSize, MIN_PAYLOAD_SIZE)
  const highestBit = Math.floor(Math.log2(size))
  const bound = Math.ceil(FR_RATIO * 2 ** (highestBit + 1))
  return size <= bound ? bound : Math.ceil(FR_RATIO * 2 ** (highestBit + 2))
}
```

### 6.4 The Filecoin Pipeline: Storefront -> Aggregator -> Dealer -> Deal-Tracker

#### 6.4.1 Capability Chain

**Key file:** `w3up/packages/capabilities/src/filecoin/storefront.js`
- `filecoin/offer` - Agent requests piece storage
- `filecoin/submit` - Storefront signals piece submitted to pipeline
- `filecoin/accept` - Storefront signals piece accepted in deal
- `filecoin/info` - Agent queries deal status

**Key file:** `w3up/packages/capabilities/src/filecoin/aggregator.js`
- `piece/offer` - Storefront offers piece to Aggregator
- `piece/accept` - Aggregator signals piece accepted into aggregate

**Key file:** `w3up/packages/capabilities/src/filecoin/dealer.js`
- `aggregate/offer` - Aggregator offers aggregate to Dealer
- `aggregate/accept` - Dealer signals aggregate accepted in deal

**Key file:** `w3up/packages/capabilities/src/filecoin/deal-tracker.js`
- `deal/info` - Query on-chain deal status

#### 6.4.2 Storefront Service Handler

**Key file:** `w3up/packages/filecoin-api/src/storefront/service.js`

`filecoin/offer` handler - entry point for the pipeline:

```js
// service.js lines 21-78
export const filecoinOffer = async ({ capability }, context) => {
  const { piece, content } = capability.nb
  const hasRes = await context.pieceStore.has({ piece })
  if (!hasRes.ok) {
    // Queue the piece for validation
    const queueRes = await context.filecoinSubmitQueue.add({ piece, content, group })
  }
  // Create effects for receipt chain: fork to submit, join to accept
  const [submitfx, acceptfx] = await Promise.all([
    StorefrontCaps.filecoinSubmit.invoke({...}).delegate(),
    StorefrontCaps.filecoinAccept.invoke({...}).delegate(),
  ])
  const result = Server.ok({ piece })
  return result.fork(submitfx.link()).join(acceptfx.link())
}
```

`filecoin/submit` handler - queues piece/offer to aggregator:

```js
// service.js lines 85-126
export const filecoinSubmit = async ({ capability }, context) => {
  const { piece, content } = capability.nb
  // Queue `piece/offer` invocation
  const res = await context.pieceOfferQueue.add({ piece, content, group })
  // Create effect: joins to piece/offer
  const fx = await AggregatorCaps.pieceOffer.invoke({
    issuer: context.id, audience: context.aggregatorId,
    with: context.id.did(), nb: { piece, group },
  }).delegate()
  const result = Server.ok({ piece })
  return result.join(fx.link())
}
```

`filecoin/accept` handler - follows receipt chain to find aggregation proof:

```js
// service.js lines 133-176
export const filecoinAccept = async ({ capability }, context) => {
  const { piece } = capability.nb
  const getPieceRes = await context.pieceStore.get({ piece })
  // ... recreate the piece/offer invocation to find its receipt chain
  const dataAggregationProof = await findDataAggregationProof(context, fx.link())
  return {
    ok: {
      aux: dataAggregationProof.ok.aux,
      inclusion: dataAggregationProof.ok.inclusion,
      piece,
      aggregate: dataAggregationProof.ok.aggregate,
    },
  }
}
```

#### 6.4.3 Aggregator Service Handler

**Key file:** `w3up/packages/filecoin-api/src/aggregator/service.js`

`piece/offer` handler - queues piece for inclusion in aggregate:

```js
// service.js lines 20-62
export const pieceOffer = async ({ capability }, context) => {
  const { piece, group } = capability.nb
  if (!hasRes.ok) {
    const addRes = await context.pieceQueue.add({ piece, group })
  }
  const fx = await AggregatorCaps.pieceAccept.invoke({
    issuer: context.id, audience: context.id,
    with: context.id.did(), nb: { piece, group },
  }).delegate()
  const result = Server.ok({ piece })
  return result.join(fx.link())
}
```

`piece/accept` handler - returns inclusion proof and chains to aggregate/offer:

```js
// service.js lines 69-120
export const pieceAccept = async ({ capability }, context) => {
  const { piece, group } = capability.nb
  // Get inclusion proof for this piece in aggregate
  const getInclusionRes = await context.inclusionStore.query({ piece, group })
  const [{ aggregate, inclusion }] = getInclusionRes.ok.results
  // Get aggregate details
  const getAggregateRes = await context.aggregateStore.get({ aggregate })
  // Chain to aggregate/offer on the Dealer
  const fx = await DealerCaps.aggregateOffer.invoke({
    issuer: context.id, audience: context.dealerId,
    with: context.id.did(), nb: { aggregate, pieces: getAggregateRes.ok.pieces },
  }).delegate()
  const result = Server.ok({ piece, aggregate, inclusion })
  return result.join(fx.link())
}
```

#### 6.4.4 Dealer Service Handler

**Key file:** `w3up/packages/filecoin-api/src/dealer/service.js`

`aggregate/offer` handler - stores aggregate offer for Spade:

```js
// service.js lines 22-95
export const aggregateOffer = async ({ capability, invocation }, context) => {
  const { aggregate, pieces } = capability.nb
  if (!hasRes.ok) {
    // Write Spade formatted doc to offerStore
    const putOfferRes = await context.offerStore.put({
      key: piecesBlockRes.ok.cid.toString(),
      value: { issuer, aggregate, pieces: piecesBlockRes.ok.value },
    })
    // Put aggregate into tracking store
    await context.aggregateStore.put({
      aggregate, pieces, status: 'offered',
      insertedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    })
  }
  const fx = await DealerCaps.aggregateAccept.invoke({...}).delegate()
  const result = Server.ok({ aggregate })
  return result.join(fx.link())
}
```

`aggregate/accept` handler - checks deal-tracker for on-chain deals:

```js
// service.js lines 102-150
export const aggregateAccept = async ({ capability }, context) => {
  const { aggregate } = capability.nb
  const info = await DealTracker.dealInfo(
    context.dealTrackerService.invocationConfig, aggregate,
    { connection: context.dealTrackerService.connection }
  )
  const deals = Object.keys(info.out.ok.deals || {})
  if (!deals.length) {
    return { error: new Server.Failure('no deals were obtained...') }
  }
  return {
    ok: {
      aggregate,
      dataSource: { dealID: BigInt(deals[0]) },
      dataType: 0n,
    },
  }
}
```

#### 6.4.5 Deal Tracker Service

**Key file:** `w3up/packages/filecoin-api/src/deal-tracker/service.js`

`deal/info` handler - queries on-chain deal records:

```js
// service.js lines 19-46
export const dealInfo = async ({ capability }, context) => {
  const { piece } = capability.nb
  const records = []
  let cursor
  do {
    const storeQuery = await context.dealStore.query({ piece }, { cursor })
    records.push(...storeQuery.ok.results)
    cursor = storeQuery.ok.cursor
  } while (cursor)
  return {
    ok: {
      deals: records.reduce((acc, curr) => {
        acc[`${curr.dealId}`] = { provider: curr.provider }
        return acc
      }, {}),
    },
  }
}
```

### 6.5 Inclusion Proofs

**Key file:** `data-segment/src/inclusion.js`

An inclusion proof is a pair `[tree_proof, index_proof]` that proves a piece is included in an aggregate:

```js
// inclusion.js lines 48-58
export const from = ([tree, index]) => [Proof.from(tree), Proof.from(index)]

export const create = ({ tree, index }) => [tree, index]
```

The `resolveAggregate` function verifies the inclusion proof resolves back to the claimed aggregate:

```js
// inclusion.js lines 86-110
export const resolveAggregate = (proof, segmentPiece) => {
  const piece = Piece.fromLink(segmentPiece)
  const tree = Inclusion.tree(proof)
  const index = Inclusion.index(proof)

  const { ok: aggregate, error } = resolveAggregateFromProofTree({ tree }, piece)
  if (error) return { error }

  const result = resolveAggregateFromProofIndex({ index, tree }, piece)
  if (result.error) return result

  if (aggregate.toString() !== result.ok.toString()) {
    return { error: new Error('Inclusion proof is invalid') }
  }
  return { ok: aggregate }
}
```

### 6.6 Data Aggregation (Piri Go Implementation)

**Key file:** `piri/pkg/pdp/aggregation/aggregator/aggregate.go`

The Go aggregator builds Merkle trees over sorted piece commitments:

```go
// aggregate.go lines 38-58
func NewAggregate(pieceLinks []piece.PieceLink) (types.Aggregate, error) {
    if len(pieceLinks) == 0 {
        return types.Aggregate{}, errors.New("no pieces provided")
    }
    todo := make([]stackFrame, len(pieceLinks))
    lastSize := uint64(0)
    for i, p := range pieceLinks {
        if p.PaddedSize() < 128 {
            return types.Aggregate{}, fmt.Errorf("invalid Size of PieceInfo %d: too small", i)
        }
        if lastSize > 0 && p.PaddedSize() > lastSize {
            return types.Aggregate{}, fmt.Errorf("pieces are not sorted correctly largest to smallest")
        }
        todo[i] = stackFrame{size: p.PaddedSize(), commP: p.DataCommitment()}
        lastSize = p.PaddedSize()
    }
    // ... stack-based tree construction with zero-padding ...
}
```

### 6.7 PDP (Provable Data Possession) - Piri

**Key file:** `piri/pkg/pdp/types/api.go`

PDP types define proof sets with on-chain verification via Ethereum:

```go
// api.go lines 14-36
type ProofSet struct {
    ID                     uint64
    Initialized            bool
    NextChallengeEpoch     int64
    PreviousChallengeEpoch int64
    ProvingPeriod          int64
    ChallengeWindow        int64
    Roots                  []RootEntry
}

type ProofSetAPI interface {
    CreateProofSet(ctx context.Context) (common.Hash, error)
    GetProofSetStatus(ctx context.Context, txHash common.Hash) (*ProofSetStatus, error)
    GetProofSet(ctx context.Context, proofSetID uint64) (*ProofSet, error)
    AddRoots(ctx context.Context, proofSetID uint64, roots []RootAdd) (common.Hash, error)
    RemoveRoot(ctx context.Context, proofSetID uint64, rootID uint64) (common.Hash, error)
}
```

**Key file:** `piri/pkg/service/storage/handlers/blob/accept.go`

The blob/accept handler in Piri integrates PDP. On accept, it:
1. Verifies blob exists
2. Gets download URL
3. **Enqueues CommP calculation** via `s.PDP().CommpCalculate().Enqueue()`
4. Creates a `pdp/accept` invocation (resolves when aggregation completes)
5. Creates an `assert/location` claim delegation
6. Publishes the location claim

```go
// accept.go lines 88-125
// submit the piece for aggregation
if err := s.PDP().CommpCalculate().Enqueue(ctx, req.Blob.Digest); err != nil {
    return nil, fmt.Errorf("submitting piece for aggregation: %w", err)
}
// generate invocation that will complete when aggregation is complete
pieceAccept, err := pdp_cap.Accept.Invoke(s.ID(), s.ID(), s.ID().DID().String(),
    pdp_cap.AcceptCaveats{Blob: req.Blob.Digest}, delegation.WithNoExpiration())
// ...
claim, err := assert.Location.Delegate(s.ID(), req.Space, s.ID().DID().String(),
    assert.LocationCaveats{
        Space: req.Space, Content: types.FromHash(req.Blob.Digest),
        Location: []url.URL{loc}, Range: &byteRange,
    }, delegation.WithNoExpiration(),
)
```

**Key file:** `piri/pkg/service/storage/ucan/pdp_info.go`

The `pdp/info` handler resolves a blob to its CommP piece CID:

```go
// pdp_info.go lines 40-68
func WithPDPInfoMethod(storageService PDPInfoService) server.Option {
    return server.WithServiceMethod(
        pdp.InfoAbility,
        server.Provide(pdp.Info, func(ctx context.Context, cap ucan.Capability[pdp.InfoCaveats], ...) (...) {
            // resolve blob to its derived pieceCID (commp)
            resolvedCommp, found, err := storageService.PDP().API().ResolveToPiece(ctx, cap.Nb().Blob)
            if !found {
                // compute on demand if not yet computed
                commpResp, err := storageService.PDP().API().CalculateCommP(ctx, cap.Nb().Blob)
                // return with empty aggregates (still pending)
                return result.Ok(pdp.InfoOk{Piece: pieceLink, Aggregates: []pdp.InfoAcceptedAggregate{}})
            }
            // look up receipt for the accept invocation
            rcpt, err := storageService.Receipts().GetByRan(ctx, pieceAccept.Link())
            // ... return piece info with aggregation details
        }),
    )
}
```

### 6.8 Storefront Events - Pipeline Workflow

**Key file:** `w3up/packages/filecoin-api/src/storefront/events.js`

After piece insertion, an `assert/equals` claim links content CID to piece CID:

```js
// events.js lines 131-154
export const handlePieceInsertToEquivalencyClaim = async (context, record) => {
  const claimResult = await Assert.equals
    .invoke({
      issuer: context.claimsService.invocationConfig.issuer,
      audience: context.claimsService.invocationConfig.audience,
      with: context.claimsService.invocationConfig.with,
      nb: {
        content: record.content,    // blob/CAR CID
        equals: record.piece,       // piece/CommP CID
      },
      expiration: Infinity,
      proofs: context.claimsService.invocationConfig.proofs,
    })
    .execute(context.claimsService.connection)
}
```

### 6.9 CommP Calculation Pipeline (Piri)

**Key file:** `piri/pkg/pdp/aggregation/commp/commp.go`

CommP calculation is a queued async job:

```go
// commp.go lines 17-71
type Calculator interface {
    Enqueue(ctx context.Context, blob multihash.Multihash) error
}

type Comper struct {
    queue   jobqueue.Service[multihash.Multihash]
    handler jobqueue.TaskHandler[multihash.Multihash]
}

func (c *Comper) Enqueue(ctx context.Context, blob multihash.Multihash) error {
    log.Infow("enqueuing commp", "blob", blob.String())
    return c.queue.Enqueue(ctx, c.handler.Name(), blob)
}
```

---

## Summary: Pipeline Flow

### UCAN Auth Flow
1. Agent generates `did:key` space, calls `access/authorize` with `did:mailto` account
2. User clicks email link, triggering `access/confirm`
3. Service creates delegation (absent-signed by account) + `ucan/attest` attestation
4. Agent polls `access/claim` to retrieve session proofs
5. Agent uses proofs to invoke capabilities on the space

### Content Claims & Indexing Flow
1. Blob stored -> `assert/location` claim created (blob at URL)
2. Piece computed -> `assert/equals` claim (blob CID = piece CID)
3. Index uploaded -> `index/add` handler extracts ShardedDAGIndex
4. Index published to IPNI with `assert/index` claim
5. Queries walk: multihash -> IPNI -> equals/index/location claims -> fetch indexes -> resolve shard locations

### Filecoin Pipeline Flow
1. `filecoin/offer` (agent) -> queues for submit
2. `filecoin/submit` (storefront) -> validates piece, queues `piece/offer`
3. `piece/offer` (aggregator) -> queues piece for buffer/aggregate
4. Buffer fills -> aggregation produces aggregate + inclusion proofs
5. `piece/accept` (aggregator) -> returns inclusion proof, chains to `aggregate/offer`
6. `aggregate/offer` (dealer) -> stores for Spade deal-making
7. `aggregate/accept` (dealer) -> queries deal-tracker for on-chain deal
8. `deal/info` (deal-tracker) -> returns Filecoin deal ID and provider
9. `filecoin/accept` (storefront) -> follows receipt chain back to return full proof

### PDP Pipeline (Piri)
1. `blob/accept` -> enqueues CommP calculation
2. CommP job runs -> computes piece CID
3. Piece added to aggregate buffer
4. Buffer fills -> aggregate created, roots added to proof set (Ethereum smart contract)
5. Challenge issued on-chain -> node generates and submits proof
6. `pdp/info` -> returns piece info with aggregate and inclusion proof
