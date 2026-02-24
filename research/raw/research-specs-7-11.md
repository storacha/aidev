# Research Specifications: Topics 7-11

Comprehensive research report covering Pail & Distributed Data Structures, Gateway & Retrieval, Encryption & KMS, Go Ecosystem, and libp2p & Networking as used in the Storacha decentralized storage platform.

---

## Topic 7: Pail & Distributed Data Structures

### 7.1 Prolly Trees (Probabilistic B-Trees)

#### Concept

A Prolly Tree is a content-addressed search tree where the number of values stored in each node is determined probabilistically based on the content of the tree itself. On the read path, key-value access works like a B-tree; on the diff path, it works like a Merkle tree. The key innovation is **deterministic structure based on content**: a given set of elements always forms the same tree regardless of insertion order.

Sources: [DoltHub Blog](https://www.dolthub.com/blog/2024-03-03-prolly-trees/), [Dolt Documentation](https://docs.dolthub.com/architecture/storage-engine/prolly-tree)

#### How Split Points (Chunk Boundaries) Are Determined

Chunk boundaries are determined by **content-defined chunking** using a rolling hash function:

1. As data is inserted into the tree, a rolling hash is computed over the serialized entries.
2. A chunk boundary (split point) occurs when the rolling hash value matches a specific, low-probability pattern -- for example, when the hash ends with a certain number of zero bits.
3. The rolling hash is **deterministic** (history-independent) and makes decisions **locally** -- it only considers the content at the current position, not how or when the data was inserted.
4. The probability of a boundary is tuned to achieve a target average chunk size. In Dolt's implementation, chunks average ~4 KB, giving roughly a 1/4096 probability of triggering a boundary on any given byte change.
5. Because the rolling hash is deterministic on content, two trees with identical data will always have identical chunk boundaries and thus identical structure, producing the same root hash.

This is analogous to how content-defined chunking works in file deduplication (e.g., Rabin fingerprinting), but applied to tree node boundaries.

#### Merkle Properties

Each node contains a cryptographic hash computed from its own content and the hashes of its children. This provides:
- **Structural sharing**: Unchanged subtrees between two versions share the same CID.
- **Efficient diffs**: Comparing two trees requires only walking the nodes whose hashes differ -- O(log n) time for point changes.
- **Proofs of inclusion/exclusion**: The hash chain from root to leaf provides a verifiable proof.

#### Relationship to Pail

Pail does NOT use prolly trees directly. Pail is a **sharded DAG-based key-value store** that uses a different approach -- prefix-based trie sharding (see Section 7.4 below). However, prolly trees represent the broader design space that Pail inhabits: content-addressed ordered data structures with structural sharing.

### 7.2 CRDTs (Conflict-free Replicated Data Types)

#### Overview

CRDTs are data structures replicated across multiple nodes that automatically resolve inconsistencies without coordination. Formally defined in 2011 by Marc Shapiro, Nuno Preguica, Carlos Baquero, and Marek Zawirski.

Sources: [Wikipedia](https://en.wikipedia.org/wiki/Conflict-free_replicated_data_type), [CRDT.tech](https://crdt.tech/), [Formal Paper (HAL)](https://inria.hal.science/hal-00932836/document)

#### State-Based CRDTs (CvRDTs)

State-based CRDTs (Convergent Replicated Data Types) are defined by:
- A **state type** S with a partial order
- An **initial state** function
- An **update** function (for local mutations)
- A **merge** function: S x S -> S

The merge function must satisfy three properties:
- **Commutative**: merge(a, b) = merge(b, a)
- **Associative**: merge(merge(a, b), c) = merge(a, merge(b, c))
- **Idempotent**: merge(a, a) = a

These properties form a **join-semilattice**, guaranteeing that replicas converge to the same state regardless of message ordering, duplication, or delays.

#### Key CRDT Types for Sets and Maps

- **G-Set (Grow-only Set)**: Elements can only be added, never removed. Merge = set union.
- **2P-Set (Two-Phase Set)**: Maintains an add-set and a remove-set. Once removed, an element cannot be re-added.
- **OR-Set (Observed-Remove Set)**: Each add is tagged with a unique ID. Remove only removes observed tags, allowing re-addition. This is the most commonly used set CRDT.
- **OR-Map**: A map where each key is associated with an OR-Set of tagged values. Provides clean semantics for concurrent updates to different keys.
- **LWW-Register (Last-Writer-Wins)**: Uses timestamps to resolve conflicts; the most recent write wins.

#### Delta CRDTs

Delta-state CRDTs optimize bandwidth by transmitting only the recently changed portion of the state (the "delta") rather than the entire state. The delta is itself a valid state that can be merged, preserving all CRDT guarantees.

#### Relevance to Pail

Pail's CRDT module (`src/crdt/index.js`) implements a state-based CRDT over the key-value store using a Merkle clock for causal ordering and deterministic merge based on event replay (see Section 7.3 and 7.4).

### 7.3 Merkle Clock and Causal Ordering

#### Vector Clocks (Background)

Vector clocks track causal ordering in distributed systems:
- Each process maintains a vector of logical timestamps, one per process.
- On local event: increment own counter.
- On send: attach current vector to message.
- On receive: element-wise max of local vector and received vector, then increment own counter.
- Comparison: V1 < V2 iff all elements of V1 <= V2 and at least one is strictly less.
- If neither V1 < V2 nor V2 < V1, the events are **concurrent**.

Sources: [Wikipedia - Vector Clock](https://en.wikipedia.org/wiki/Vector_clock), [Kevin Sookocheff](https://sookocheff.com/post/time/vector-clocks/)

#### Merkle Clocks

A Merkle Clock is a **Merkle DAG where each node represents an event**. It combines:
- The causal ordering properties of vector clocks
- The content-addressing and deduplication properties of Merkle DAGs

Source: [Merkle-CRDTs paper (Protocol Labs)](https://research.protocol.ai/publications/merkle-crdts-merkle-dags-meet-crdts/psaras2020.pdf)

Key properties:
1. **Events are immutable and content-addressed**: Each event is a DAG node with a CID.
2. **Parent links encode causality**: An event's parents are the events it "happened after."
3. **Multiple heads = concurrent events**: When the clock has multiple head CIDs, those events are concurrent (like concurrent entries in a vector clock).
4. **Equality by root hash**: Two clocks with the same root hash have the same history.
5. **Efficient sync via DAG walking**: Determining the diff between two clocks requires only walking differing nodes.

#### Merkle Clock Merge Rules

Given two Merkle Clock states T1 and T2:
- If T1 = T2 (same root hashes): no merge needed.
- If T1 is a subset of T2 (T1's head is an ancestor of T2's head): keep T2.
- If T2 is a subset of T1: keep T1.
- If neither is a subset: both heads are kept (concurrent). A new event then creates a merge node with both as parents.

#### Storacha's w3-clock Specification

From the local spec at `specs/w3-clock.md`:

**Data format** (IPLD Schema):
```ipldsch
type Event struct {
  parents [&Event]
  data &Data
}
type Data = Any
```

- `parents`: Array of zero or more links to preceding events. Parents MUST be the current head of the clock. Parents MUST be sorted in ascending byte order of the binary encoding of the link.
- `data`: Application-specific data describing the operation.

**Two capabilities**:
- `clock/advance`: Adds a new event to the clock. The event block and ancestor events MAY be sent with the invocation. A successful invocation returns the new head.
- `clock/head`: Fetches the current head (array of CIDs to the most recent events).

#### Pail's Clock Implementation

From `pail/src/clock/index.js`:

The `advance(blocks, head, event)` function:
1. If the event is already in the head, return unchanged.
2. Check if the new event **contains** (is an ancestor of) any current head events. If so, those head events are replaced by the new event.
3. Check if any current head event contains the new event. If so, the event is already known -- return unchanged.
4. Otherwise, the event is **concurrent** -- append it to the head array.

The `contains(events, a, b)` function performs a **breadth-first search** from event `a` backward through parents to determine if event `b` is an ancestor of `a`.

Events are encoded as DAG-CBOR blocks with SHA-256 hashing. Parents are sorted by binary byte order before encoding to ensure deterministic CIDs.

### 7.4 Pail: Sharded DAG Key-Value Store

From `pail/README.md` and source code:

#### Architecture

Pail is a **DAG-based key-value store** where:
- Keys are strings (printable ASCII, max 4096 bytes UTF-8 encoded).
- Values are CIDs (links to arbitrary IPLD data).
- The data structure is a **prefix trie** of shards, where each shard is a DAG-CBOR encoded block.

#### Shard Structure

Each shard contains:
- `entries`: Array of `[key_suffix, value]` pairs, where value is either a CID (leaf) or `[shard_link]` (pointer to child shard) or `[shard_link, CID]` (both a value and a child shard pointer).
- `version`: Always 1.
- `keyChars`: Character set (default "ascii").
- `maxKeySize`: Maximum key size in bytes (default 4096).
- `prefix`: The accumulated key prefix for this shard (enables key reconstruction during traversal).

#### Put Operation

The `put(blocks, root, key, value)` operation:
1. Traverses from the root shard following key prefixes to find the target shard.
2. If the key already exists as an exact match, its value is replaced.
3. If a new key shares a common prefix with an existing entry, the shard is **split**: a new child shard is created with entries for both the existing and new keys (minus the common prefix), and the parent gets a link to the new child shard.
4. Changes propagate upward: each modified shard gets a new CID, and parent shards are re-encoded with updated child links, all the way to a new root CID.
5. Returns `{ root, additions, removals }` -- the new root CID, new blocks to store, and old blocks that can be garbage collected.

#### CRDT Merge Semantics for Concurrent Writes

From `pail/src/crdt/index.js`:

The CRDT layer wraps the base Pail operations with a Merkle clock:

1. **Each mutation is an event**: A `put` creates an event with `{ type: 'put', root, key, value }` data, linking to the current head as parents.
2. **Finding common ancestor**: When the head has multiple entries (concurrent writes), `findCommonAncestor` walks backwards through the DAG to find the first event that all head branches share.
3. **Deterministic replay**: `findSortedEvents` collects all events between the common ancestor and the heads, then sorts them by:
   - **Weight** (depth from head -- heavier/deeper events happened earlier and are replayed first).
   - **CID string comparison** as tiebreaker within the same weight.
4. **Sequential replay**: Events are replayed in sorted order on top of the common ancestor's root, producing a deterministic merged state.
5. **New event appended**: The current mutation is then applied on top of the merged state, and a new event is created with all current heads as parents (resolving the concurrent fork).

From `pail/src/merge.js`:

The standalone `merge(blocks, base, targets)` function:
1. Computes diffs between the base and each target using `difference()`.
2. Replays all diffs sequentially (puts and deletes) on top of the base.
3. Returns the merged root with additions and removals.

This approach ensures that regardless of the order concurrent writes arrived at different replicas, the merge produces the same deterministic result -- satisfying CRDT convergence requirements.

---

## Topic 8: Gateway & Retrieval (IPFS Gateway Spec)

### 8.1 IPFS Path Gateway Specification

Source: [IPFS Path Gateway Spec](https://specs.ipfs.tech/http-gateways/path-gateway/)

#### Path Resolution (`/ipfs/CID/path`)

1. The gateway takes the URL path and splits it into two parts:
   - **Content root CID**: The CID provides the starting point for data retrieval.
   - **Remainder path**: Instructions to traverse IPLD data starting from the root CID.

2. Resolution process:
   - The CID is resolved to its corresponding IPLD block.
   - If a remainder path exists, it is traversed according to the data type:
     - **UnixFS pathing**: For files and directories encoded with UnixFS.
     - **DAG-JSON / DAG-CBOR pathing**: For structured IPLD data, traversing map keys.
   - Each path segment resolves through the IPLD graph until the target entity is reached.

3. Example: `GET /ipfs/bafyROOT/images/photo.jpg`
   - Resolves `bafyROOT` to a UnixFS directory.
   - Traverses `images` -> `photo.jpg` through the directory tree.
   - Returns the file bytes.

#### Content Type Negotiation

- Based on Section 12.5.1 of RFC 9110.
- Clients can request specific formats via the `Accept` header:
  - `application/vnd.ipld.raw` -- raw block bytes
  - `application/vnd.ipld.car` -- CAR (Content Addressable aRchive) stream
  - `application/json`, `application/cbor` -- deserialized formats
- The `format` query parameter provides an alternative: `?format=raw`, `?format=car`
- Both should be included for best interoperability and consistent HTTP cache behavior.

#### Caching Headers

- **ETag**: Based on the requested CID, wrapped in double quotes per RFC 9110 Section 8.8.3.
  - Default: `Etag: "bafyFOO"` based on the requested CID.
  - For custom formats: modified to include format, e.g., `Etag: "bafyFOO.raw"`.
  - For generated HTML directory indexes: based on gateway implementation version.
- **Cache-Control**: Immutable content (raw CID responses) can use aggressive caching. Mutable references (IPNS) require revalidation.
- **If-None-Match**: Standard conditional request support.
- **`Cache-Control: only-if-cached`**: IPFS-aware clients can probe gateways that already have data cached, improving retrieval speed.

### 8.2 IPFS Trustless Gateway Specification

Source: [IPFS Trustless Gateway Spec](https://specs.ipfs.tech/http-gateways/trustless-gateway/)

#### Overview

The Trustless Gateway is a minimal subset of the Path Gateway that facilitates data retrieval via CID while ensuring **integrity verification** -- eliminating the need to trust the gateway.

#### Response Formats

**Raw blocks** (`application/vnd.ipld.raw`):
- Request: `GET /ipfs/{cid}?format=raw` or `Accept: application/vnd.ipld.raw`
- Response: The raw bytes of the single block identified by the CID.
- Verification: The client hashes the response bytes using the algorithm specified in the CID's multihash. If the hash matches the CID, the data is authentic. If not, the response is treated as an error.

**CAR streams** (`application/vnd.ipld.car`):
- Request: `GET /ipfs/{cid}[/path]?format=car` or `Accept: application/vnd.ipld.car`
- Response: A CAR v1 stream containing the blocks needed to verify the path.
- Content-Type MUST include version: `Content-Type: application/vnd.ipld.car; version=1`
- Parameters:
  - `order=dfs|unk` -- block ordering (depth-first or unknown)
  - `dups=y|n` -- whether duplicate blocks are included
  - `dag-scope=block|entity|all` -- scope of blocks included:
    - `block`: Only the root block.
    - `entity`: Blocks needed to verify the entity at the path (e.g., all chunks of a UnixFS file).
    - `all`: All blocks in the DAG rooted at the CID.

#### Key Protocol Details

- A gateway MUST return HTTP 400 Bad Request in strict trustless mode if the `Accept` header is missing.
- A gateway MUST return 404 Not Found when the root block is not available. For non-recursive gateways, this definitively signals the content is not in the gateway's dataset.
- Block size: Implementations MUST support blocks up to 2 MiB (matching Bitswap limits).
- The client SHOULD include both the `format` query parameter and `Accept` header for maximum interoperability.

### 8.3 Content-Serve Authorization (Storacha-specific)

From `specs/content-serve-auth.md`:

#### Overview

Storacha's Content Server Authorization ensures that access to content is governed by UCAN delegations. Content owners delegate retrieval capabilities to specific gateway services, ensuring only authorized entities can serve the content.

#### Key Concepts

- **Space**: A logical container for data, identified by a DID.
- **Delegation**: Granting the `space/content/serve` capability to a gateway via UCAN.
- **Gateway**: An IPFS gateway that ALSO enforces UCAN authorization policies.
- **Delegations Store**: Where the gateway stores and manages received delegations.

#### Delegation Flow

1. **Client creates a UCAN delegation** granting `space/content/serve` to the Gateway (identified by a DID like `did:web:storacha.link`).
   ```json
   {
     "iss": "did:key:zAlice",
     "aud": "did:web:storacha.link",
     "att": [{ "can": "space/content/serve", "with": "did:key:zSpace" }]
   }
   ```
2. **Client wraps the delegation** in an `access/delegate` UCAN invocation.
3. **Client sends the invocation** (CAR-encoded) to the Gateway via `POST /`.
4. **Gateway validates** the delegation chain and stores it in the Delegations Store.

#### Content Retrieval Flow

1. Client sends `GET /ipfs/:cid` -- **no UCAN signature needed** on the HTTP request.
2. Gateway resolves the CID to a Space DID by querying the Indexer Service and checking Location Claims.
3. Gateway retrieves stored `space/content/serve` delegations for that Space from the Delegations Store.
4. Gateway **self-authorizes**: creates a UCAN invocation authorizing itself using the stored delegations as proofs.
5. Gateway validates its own invocation. If valid, content is served; otherwise, 403 Forbidden.

#### Important Design Points

- HTTP clients do NOT need DIDs or UCAN signatures -- they are not UCAN principals.
- Authorization is between the Gateway and Space owners via stored delegations.
- Multiple delegations can exist for the same space.
- Legacy spaces (pre-authorization) are served without authorization checks.
- The authorization is per-space, not per-CID (though future versions may support CID-level restrictions).

---

## Topic 9: Encryption & KMS

### 9.1 ECDH Key Agreement (P-256)

Source: [Wikipedia - ECDH](https://en.wikipedia.org/wiki/Elliptic-curve_Diffie%E2%80%93Hellman)

#### Algorithm

Elliptic Curve Diffie-Hellman (ECDH) is a key agreement protocol allowing two parties to establish a shared secret over an insecure channel:

1. **Setup**: Both parties agree on an elliptic curve and a base point G (for P-256, these are fixed by the NIST standard).
2. **Key Generation**:
   - Alice generates private key `a` (random integer) and public key `A = a * G` (scalar multiplication on the curve).
   - Bob generates private key `b` and public key `B = b * G`.
3. **Key Agreement**:
   - Alice computes `S = a * B = a * b * G`
   - Bob computes `S = b * A = b * a * G`
   - Both arrive at the same point S on the curve.
4. **Shared Secret**: The x-coordinate of point S is the shared secret (256 bits for P-256).

#### Key Variants

- **Static ECDH**: Both parties use long-term key pairs. Provides authentication but not forward secrecy.
- **Ephemeral ECDH (ECDHE)**: One or both parties generate fresh key pairs per session. Provides forward secrecy.

#### Important Notes

- The shared secret MUST NOT be used directly as a symmetric key. It should be passed through a Key Derivation Function (KDF) such as HKDF.
- P-256 (also known as secp256r1 or prime256v1) produces a 256-bit shared secret.
- NIST P-256 is widely supported in hardware (TPMs, secure enclaves) and all major TLS implementations.

### 9.2 AES-GCM Authenticated Encryption

Sources: [NIST SP 800-38D](https://csrc.nist.gov/publications/detail/sp/800-38d/final), [RFC 5116](https://datatracker.ietf.org/doc/html/rfc5116)

#### How AES-GCM Works

AES-GCM (Galois/Counter Mode) provides both **confidentiality** (encryption) and **integrity** (authentication) in a single operation:

1. **Inputs**:
   - **Key**: 128, 192, or 256-bit AES key.
   - **Nonce/IV**: Initialization vector (recommended 96 bits / 12 bytes).
   - **Plaintext**: Data to encrypt.
   - **AAD** (Additional Authenticated Data): Optional data that is authenticated but not encrypted (e.g., headers).

2. **Encryption Process**:
   - The nonce is combined with a counter to produce a sequence of counter blocks.
   - Each counter block is encrypted with AES to produce a keystream.
   - Plaintext is XORed with the keystream to produce ciphertext (CTR mode).
   - A GHASH (Galois field multiplication) is computed over the AAD and ciphertext.
   - The GHASH output is encrypted to produce the **authentication tag** (typically 128 bits).

3. **Output**: Ciphertext + Authentication Tag.

4. **Decryption**: Reverses the process. The authentication tag is verified FIRST; if it does not match, decryption fails and no plaintext is released.

#### Nonce Handling

- **CRITICAL REQUIREMENT**: Each nonce MUST be unique for a given key. Reusing a nonce with the same key completely breaks both confidentiality and authenticity.
- Recommended size: 96 bits (12 bytes). This is split internally into a 96-bit per-message nonce and a 32-bit block counter (max 2^32 blocks = ~64 GB per message).
- Nonce generation strategies:
  - **Counter-based**: Incrementing counter (safest, no collision risk).
  - **Random**: 96 random bits (acceptable for limited number of messages -- birthday bound at ~2^48 messages).
- Per NIST SP 800-38D, the nonce can be 1 to 2^64 bits, but 96 bits provides optimal performance.

### 9.3 KEK/DEK Envelope Encryption Pattern

Sources: [Google Cloud KMS Docs](https://docs.cloud.google.com/kms/docs/envelope-encryption), [NIST Glossary](https://csrc.nist.gov/glossary/term/key_encryption_key)

#### Pattern Overview

Envelope encryption uses two layers of keys:

- **DEK (Data Encryption Key)**: A symmetric key (e.g., AES-256) that encrypts the actual data. Generated randomly per file/session/resource. Short-lived.
- **KEK (Key Encryption Key)**: A higher-level key used to encrypt (wrap) the DEK. Typically long-lived and stored in an HSM or KMS. Never directly touches the data.

#### Encryption Flow

1. Generate a random DEK.
2. Encrypt the data with the DEK (e.g., AES-GCM).
3. Encrypt (wrap) the DEK with the KEK.
4. Store the encrypted data alongside the wrapped DEK.
5. Discard the plaintext DEK from memory.

#### Decryption Flow

1. Retrieve the encrypted data and wrapped DEK.
2. Send the wrapped DEK to the KMS for unwrapping (the KEK never leaves the KMS).
3. Use the unwrapped DEK to decrypt the data.
4. Discard the plaintext DEK from memory.

#### Advantages

- **Key rotation without re-encryption**: Rotate the KEK by re-wrapping DEKs with the new KEK. The data itself does not need to be re-encrypted.
- **Scalability**: One KEK can protect millions of DEKs.
- **Security boundary**: The KEK stays within the KMS/HSM hardware boundary.
- **Granularity**: Each piece of data can have its own DEK, limiting blast radius of key compromise.

### 9.4 Storacha's UCAN KMS Implementation

From `ucan-kms/README.md` and source code:

#### Architecture

The UCAN KMS is a Cloudflare Worker-based service that integrates with **Google Cloud KMS** for key management, protected by **UCAN-based authorization**.

#### Key Operations

**Encryption Setup** (`space/encryption/setup`):
1. Client sends a UCAN invocation requesting encryption setup for a space.
2. The handler validates the UCAN invocation and checks that the space has a paid plan.
3. Google KMS is called to create (or retrieve) an **RSA-OAEP-3072-SHA256** asymmetric key pair for the space.
4. The KMS key ID is derived from the sanitized Space DID.
5. The public key (PEM format) and algorithm are returned to the client.
6. The private key NEVER leaves Google KMS.

**Key Decryption** (`space/encryption/key/decrypt`):
1. Client sends a UCAN invocation with an `encryptedSymmetricKey` (the wrapped DEK).
2. The handler validates the UCAN, checks the subscription status, and verifies revocation status.
3. The encrypted symmetric key is sent to Google KMS for **asymmetric decryption** using the space's RSA private key.
4. The decrypted symmetric key is returned to the client (base64-encoded via multiformats).

#### Envelope Encryption Pattern in Storacha

Storacha uses a variant of the KEK/DEK pattern where:
- The **KEK** is an RSA-3072 asymmetric key pair managed by Google KMS (per space).
- The **DEK** is a symmetric key (likely AES-GCM) generated client-side for encrypting content.
- The DEK is encrypted (wrapped) using the space's RSA public key on the client side.
- Decryption of the DEK requires a UCAN-authorized request to the KMS service, which uses the RSA private key (never exposed) to unwrap the DEK.

#### Security Features

- UCAN-based fine-grained access control.
- Audit logging for all security-sensitive operations.
- Rate limiting and abuse protection.
- Sensitive data wrapped in `SecureString` class for memory hygiene (auto-zeroing on disposal).
- Revocation checking before key decryption.
- Generic error messages returned to clients to prevent information leakage.

---

## Topic 10: Go Ecosystem

### 10.1 go-ipld-prime

Source: [GitHub](https://github.com/ipld/go-ipld-prime), [pkg.go.dev](https://pkg.go.dev/github.com/ipld/go-ipld-prime)

#### Overview

go-ipld-prime is the canonical Go implementation of the IPLD Data Model. It provides:
- Core interfaces for IPLD Nodes
- Codec implementations (DAG-CBOR, DAG-JSON)
- IPLD Schemas support
- Traversal and transformation tools
- ADL (Advanced Data Layout) support

#### Node Interface

The `Node` interface is the fundamental read-only type for inspecting IPLD data:
```go
type Node interface {
    Kind() Kind                          // Returns the IPLD data model kind
    LookupByString(key string) (Node, error)  // Map lookup
    LookupByIndex(idx int64) (Node, error)    // List lookup
    LookupBySegment(seg PathSegment) (Node, error)
    MapIterator() MapIterator
    ListIterator() ListIterator
    Length() int64
    IsAbsent() bool
    IsNull() bool
    AsBool() (bool, error)
    AsInt() (int64, error)
    AsFloat() (float64, error)
    AsString() (string, error)
    AsBytes() ([]byte, error)
    AsLink() (Link, error)
    Prototype() NodePrototype
}
```

#### NodeBuilder / NodeAssembler Pattern

This is a two-phase construction pattern:

- **NodeBuilder**: Allocates memory and begins assembly of a value. Used at the root level. Implements `NodeAssembler`.
  ```go
  builder := basicnode.Prototype.Map.NewBuilder()
  ```
- **NodeAssembler**: Fills up pre-allocated memory. Used recursively for nested structures. Does NOT allocate new memory.
  ```go
  ma, _ := builder.BeginMap(2)
  ma.AssembleKey().AssignString("name")
  ma.AssembleValue().AssignString("Alice")
  ma.Finish()
  node := builder.Build()
  ```

The separation allows efficient construction: `NodeBuilder` allocates once, and `NodeAssembler` fills in the data without additional allocations.

#### Node Implementations

- **`basicnode`** (`node/basicnode`): General-purpose implementation using unstructured memory (Go maps, slices). Works for any data shape. Moderate performance.
- **`bindnode`** (`node/bindnode`): Maps IPLD data to/from native Go structs via reflection. Supports IPLD Schemas. Provides a good balance between type safety and ease of use.
- **Codegen** (`schema/gen/go`): Generates type-specific Go code from IPLD Schemas. Maximum performance but requires a build step.

#### NodePrototype

`NodePrototype` describes how to create new Nodes of a particular implementation:
```go
prototype := basicnode.Prototype.Map
builder := prototype.NewBuilder()
```

Different prototypes can enforce structural constraints (via Schemas) or use different memory layouts for performance.

#### Schemas Support

The `schema` package provides typed IPLD nodes:
- `schema.TypedNode` extends `Node` with type information.
- Can validate data against schemas at construction time.
- Supports all IPLD Schema features: structs, unions, enums, links, etc.

### 10.2 go-cid

Source: [GitHub](https://github.com/ipfs/go-cid), [pkg.go.dev](https://pkg.go.dev/github.com/ipfs/go-cid)

#### Overview

go-cid implements the CID (Content Identifier) specification in Go. A CID is a self-describing content-addressed identifier with components: Version, Codec (multicodec), and Multihash.

#### CID Versions

- **CIDv0**: Legacy format. Always DagProtobuf codec + SHA2-256 hash. Encoded as base58btc. Deprecated but supported for compatibility.
- **CIDv1**: `<multibase-prefix><cid-version><multicodec-packed-content-type><multihash-content-address>`. Default encoding: base32 for v1, base58 for v0.

#### Key API Differences from JS CID

| Aspect | JS (multiformats) | Go (go-cid) |
|--------|-------------------|-------------|
| Type | Class with methods | Value type (struct) |
| Creation | `CID.create(version, codec, hash)` | `cid.NewCidV1(codec, hash)` |
| Parsing | `CID.parse(string)` | `cid.Decode(string)` |
| From bytes | `CID.decode(bytes)` | `cid.Cast(bytes)` |
| String | `.toString()` | `.String()` |
| Hash access | `.multihash` | `.Hash()` |
| Codec access | `.code` | `.Type()` |
| Equality | `.equals(other)` | `.Equals(other)` |
| Immutability | Immutable class | Value type (implicitly immutable when passed by value) |

The Go implementation uses a compact struct representation, while JS uses a class. Both support CIDv0 and CIDv1. The Go library relies on the `go-multihash` and `go-multicodec` libraries for hash and codec support.

### 10.3 go-ucanto

From `go-ucanto/README.md`:

#### Overview

go-ucanto is the Go port of the ucanto UCAN RPC library. It provides the same conceptual model as the JS version but adapted to Go idioms.

#### Client Setup (Differences from JS)

```go
// Service URL & DID
serviceURL, _ := url.Parse("https://up.web3.storage")
servicePrincipal, _ := did.Parse("did:web:web3.storage")

// HTTP transport and CAR encoding
channel := http.NewHTTPChannel(serviceURL)
conn, _ := client.NewConnection(servicePrincipal, channel)

// Signer from ed25519 key
signer, _ := ed25519.Parse(priv)

// Define capabilities using IPLD schemas
capability := ucan.NewCapability("store/add", resourceDID, caveats)

// Create and send invocations
inv, _ := invocation.Invoke(signer, audience, capability, delegation.WithProofs(...))
resp, _ := client.Execute(ctx, []invocation.Invocation{inv}, conn)
```

Key differences from JS:
- **Explicit IPLD Schema types**: Caveats must implement `ToIPLD()` returning a `datamodel.Node`. Schemas are loaded from IPLD schema DSL strings using `ipldprime.LoadSchemaBytes()`.
- **Receipt reading**: Uses a typed `ReceiptReader[OkModel, ErrModel]` with IPLD schema for result types, rather than JS's dynamic typing.
- **Context-based**: Uses Go's `context.Context` for cancellation and timeouts.

#### Server Setup (Differences from JS)

```go
// Define capabilities with validator
testecho := validator.NewCapability(
    "test/echo",
    schema.DIDString(),
    schema.Struct[TestEcho](EchoType(), nil),
    validator.DefaultDerives,
)

// Create server with handlers
server, _ := server.NewServer(
    signer,
    server.WithServiceMethod(
        testecho.Can(),
        server.Provide(testecho, handlerFunc),
    ),
)

// Wire up to HTTP
http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
    res, _ := server.Request(r.Context(), uhttp.NewHTTPRequest(r.Body, r.Header))
    // write response...
})
```

Key differences from JS:
- **No TypeScript generics**: Go uses explicit type parameters `[OkModel, ErrModel]` on receipt readers and typed capabilities `Capability[TestEcho]`.
- **IPLD schema strings**: Capability caveats and result types are defined via IPLD schema DSL strings, not TypeScript types.
- **Standard library HTTP**: Plugs directly into Go's `net/http` rather than requiring framework adapters.
- **Explicit capability wiring**: `server.WithServiceMethod()` + `server.Provide()` pattern vs. JS's object-based service definition.

### 10.4 go-libstoracha

From `go-libstoracha/README.md`:

A unified Go library (monorepo) for Storacha functionality with subpackages:

- **capabilities**: UCAN capability definitions for the Storacha ecosystem.
- **datastore**: Implementations of the IPFS Datastore interface on different backends.
- **metadata**: IPNI (InterPlanetary Network Indexer) metadata used by Storacha.
- **jobqueue**: A reliable and parallelizable job queue.
- **ipnipublisher**: Library to create, sign, and publish advertisements to a local IPNI chain, then announce them to other indexers.
- **piece**: (TODO -- likely Filecoin piece-related functionality).

---

## Topic 11: libp2p & Networking

### 11.1 libp2p Architecture Overview

Sources: [libp2p Docs](https://docs.libp2p.io/concepts/introduction/overview/), [Architecture Spec](https://github.com/libp2p/specs/blob/master/_archive/4-architecture.md)

#### Design Philosophy

libp2p is a modular network stack for building decentralized peer-to-peer applications. It follows the Unix philosophy: small, testable components that can be swapped to accommodate different technologies. Every component is a pluggable module.

#### Core Components

**Host**: The central entry point that ties all components together. A Host has:
- An identity (PeerID derived from a cryptographic key pair)
- A set of listening addresses (multiaddrs)
- A connection manager
- A stream multiplexer
- Registered protocol handlers

**PeerID**: A unique identifier for each node, derived as the cryptographic hash of the peer's public key. This provides a secure, verifiable identity that is independent of network location.

**Peer Store**: Maintains known information about peers:
- Key store: Public keys
- Address book: Known multiaddrs
- Protocol book: Supported protocols

### 11.2 Connection Lifecycle

Source: [Connection Spec](https://github.com/libp2p/specs/blob/master/connections/README.md)

#### Full Lifecycle

1. **Transport**: A raw connection is established over a transport (TCP, QUIC, WebSocket, WebTransport).
2. **Security Handshake**: The connection is upgraded with encryption:
   - Peers use **multistream-select** to negotiate the security protocol.
   - libp2p supports **TLS 1.3** and **Noise**.
   - During the security handshake, peer identities are exchanged and verified.
3. **Stream Multiplexer Negotiation**:
   - After security is established, peers negotiate a stream multiplexer (yamux, mplex).
   - **Early Multiplexer Negotiation**: Using ALPN (for TLS) or Noise extensions, the muxer can be negotiated simultaneously during the security handshake, saving a round-trip.
4. **Connection Established**: Both peers can now open multiple independent streams over the single connection.
5. **Stream Opening**: Either peer can open a new stream. Each stream has its own protocol negotiated via multistream-select.

#### Protocol Negotiation (multistream-select)

- Peers exchange the multistream protocol ID first.
- The dialing peer proposes a protocol by sending its ID.
- The listening peer responds by echoing the ID (accepted) or sending "na" (rejected).
- Protocol multiplexing happens at the application level (not port level), enabling multiple protocols over one connection.

#### Security Protocols

**TLS 1.3**:
- Standard TLS with a libp2p-specific extension to embed the peer's public key in the certificate.
- Uses ALPN for early muxer negotiation.

**Noise (XX handshake)**:
- Based on the Noise Protocol Framework.
- XX pattern: Both sides transmit their static keys during the handshake.
- Uses a libp2p-defined extension registry for muxer negotiation in the handshake payload.

### 11.3 How a libp2p Host is Constructed (Go)

```go
import "github.com/libp2p/go-libp2p"

// Basic host with defaults
host, err := libp2p.New(
    libp2p.ListenAddrStrings("/ip4/0.0.0.0/tcp/0"),
)

// Customized host
host, err := libp2p.New(
    libp2p.ListenAddrStrings(
        "/ip4/0.0.0.0/tcp/4001",
        "/ip4/0.0.0.0/udp/4001/quic-v1",
    ),
    libp2p.Identity(privKey),
    libp2p.Security(noise.ID, noise.New),
    libp2p.Security(tls.ID, tls.New),
    libp2p.Transport(tcp.NewTCPTransport),
    libp2p.Transport(quic.NewTransport),
    libp2p.Muxer("/yamux/1.0.0", yamux.DefaultTransport),
    libp2p.NATPortMap(),
    libp2p.EnableRelay(),
)
```

The `libp2p.New()` function accepts functional options to configure each layer. Sensible defaults are provided for all components.

### 11.4 Multiaddr Format

Source: [Multiformats - Multiaddr](https://multiformats.io/multiaddr/), [GitHub](https://github.com/multiformats/multiaddr)

#### Overview

Multiaddr is a self-describing, composable address format that encodes multiple layers of addressing in a single path structure. It eliminates protocol ossification by explicitly stating the protocol and transport.

#### Format

**Human-readable** (UTF-8 path notation):
```
/ip4/127.0.0.1/tcp/4001
/ip4/203.0.113.1/udp/4001/quic-v1
/ip6/::1/tcp/8080/ws
/dns4/example.com/tcp/443/https
/ip4/1.2.3.4/tcp/4001/p2p/QmPeerID
```

**Binary** (compact TLV encoding):
- Type: unsigned varint identifying the protocol (from the multicodec table).
- Length: implicit or explicit depending on the protocol.
- Value: protocol-specific address bytes.
- Recursive: multiple TLV tuples concatenated.

#### Key Properties

- **Self-describing**: Each component identifies its protocol.
- **Composable**: Layers stack naturally (IP -> TCP -> WebSocket -> p2p).
- **Extensible**: New protocols are added to the multicodec table without changing the format.
- **Transport-agnostic**: The same format works for TCP, UDP, QUIC, WebSocket, Tor, etc.

### 11.5 Pubsub / GossipSub

Sources: [GossipSub v1.0 Spec](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.0.md), [GossipSub v1.1 Spec](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.1.md), [go-libp2p-pubsub](https://github.com/libp2p/go-libp2p-pubsub)

#### Overview

GossipSub is a pubsub protocol that blends **mesh-restricted eager push** for data with **gossip-based lazy pull** for metadata. It is used in Filecoin and Ethereum 2.0.

#### Mesh Overlay

- Each peer maintains a **mesh** of D connections per topic (target degree).
- **D_low** and **D_high** are boundaries:
  - If connections > D_high: prune excess peers.
  - If connections < D_low: graft new peers.
- Mesh members are "full message" peers -- all messages in the topic are eagerly forwarded.

#### Message Propagation

1. **Eager Push (Mesh)**: When a peer receives a message, it forwards it to all mesh peers for that topic.
2. **Lazy Pull (Gossip)**: At regular intervals (heartbeat), peers emit **IHAVE** messages to a random subset of non-mesh peers, advertising message IDs they have seen recently.
3. **IWANT**: A peer that receives an IHAVE for a message it hasn't seen sends an IWANT to request the full message.

#### Heartbeat

- Runs periodically (default: 1 second).
- Performs mesh maintenance (graft/prune to maintain target degree D).
- Emits gossip (IHAVE messages) for recently seen messages.
- Shifts the message cache window (mcache) -- typically 3 heartbeat rounds of gossip history.

#### GossipSub v1.1 Enhancements

- **Peer scoring**: Peers are scored based on behavior (message delivery, protocol violations). Low-scoring peers are pruned.
- **Flood publishing**: The message originator sends to ALL connected peers with the topic, not just mesh peers, for reliable initial propagation.
- **Adaptive gossip**: Gossip factor adjusts based on topic size.
- **Opportunistic grafting**: Periodically graft high-scoring non-mesh peers to improve mesh quality.

#### Go Usage

```go
import pubsub "github.com/libp2p/go-libp2p-pubsub"

// Create GossipSub instance attached to a host
ps, err := pubsub.NewGossipSub(ctx, host)

// Join a topic
topic, err := ps.Join("my-topic")

// Subscribe to receive messages
sub, err := topic.Subscribe()

// Read messages
msg, err := sub.Next(ctx)

// Publish messages
err = topic.Publish(ctx, []byte("hello"))
```

### 11.6 Bitswap Protocol

Sources: [Bitswap Spec](https://specs.ipfs.tech/bitswap-protocol/), [IPFS Docs](https://docs.ipfs.tech/concepts/bitswap/)

#### Overview

Bitswap is a libp2p data exchange protocol for sending and receiving content-addressed blocks. It is message-based (not request-response).

#### Protocol IDs

- `/ipfs/bitswap/1.2.0` (current)
- `/ipfs/bitswap/1.1.0`
- `/ipfs/bitswap/1.0.0`
- `/ipfs/bitswap` (legacy)

#### Message Types (Wire Format)

Messages are protobuf-encoded and length-prefixed (unsigned varint):

```protobuf
message Message {
  message Wantlist {
    message Entry {
      bytes block = 1;       // CID
      int32 priority = 2;    // normalized priority
      bool cancel = 3;       // cancel previous entry
      WantType wantType = 4; // Block or Have
      bool sendDontHave = 5; // request DontHave response
    }
    repeated Entry entries = 1;
    bool full = 2;           // full wantlist (not incremental)
  }

  message Block {
    bytes prefix = 1;        // CID prefix (version + codec + hash function + hash length)
    bytes data = 2;          // block data
  }

  enum BlockPresenceType {
    Have = 0;
    DontHave = 1;
  }

  message BlockPresence {
    bytes cid = 1;
    BlockPresenceType type = 2;
  }

  Wantlist wantlist = 1;
  repeated Block payload = 3;              // Bitswap 1.1.0+
  repeated BlockPresence blockPresences = 4; // Bitswap 1.2.0+
  int32 pendingBytes = 5;
}
```

#### Block Exchange Process

1. **Peer connects**: Peers discover each other via DHT, PEX, or direct connection.
2. **Wantlist exchange**: A peer sends its wantlist (CIDs it wants) to connected peers.
3. **Want-Have / Want-Block** (v1.2.0):
   - `Want-Have`: "Do you have this block?" Peer responds with `Have` or `DontHave`.
   - `Want-Block`: "Send me this block." Peer responds by sending the block data.
   - This two-phase approach enables content routing -- find who has the block, then request it.
4. **Block delivery**: Blocks are sent in `payload` entries with CID prefix + data.
5. **Wantlist updates**: Incremental updates add/cancel entries as needs change.

#### Size Limits

- Individual blocks: MUST support up to 2 MiB. Blocks larger than 2 MiB are NOT recommended.
- Protocol messages: MUST be <= 4 MiB total.

#### Peer Discovery

- **DHT (Kademlia)**: Find providers for a given CID by looking up the DHT.
- **mDNS**: Discover peers on the local network.
- **Bootstrap nodes**: Pre-configured peers for initial discovery.
- **Bitswap itself** (v1.2.0): Acts as basic content routing for already-connected peers via Want-Have queries.

---

## Summary of Key Relationships

| Component | Role in Storacha |
|-----------|-----------------|
| Pail + Merkle Clock | CRDT-based mutable key-value store for upload metadata, enabling multi-writer convergent state |
| IPFS Gateway + Content-Serve Auth | Content retrieval with UCAN-based authorization -- gateway self-authorizes using stored delegations |
| UCAN KMS + Envelope Encryption | Client-side encryption with server-side key management -- RSA KEK in Google KMS, AES-GCM DEK client-side |
| go-ucanto + go-ipld-prime | Go implementation of UCAN RPC using IPLD data model for schema-typed capabilities |
| go-libstoracha | Shared Go libraries: capabilities, datastore, IPNI publishing, job queue |
| libp2p + Bitswap + GossipSub | Peer-to-peer networking layer for block exchange, content routing, and pubsub messaging |
| Multiaddr | Self-describing address format used throughout libp2p for transport-agnostic peer addressing |
