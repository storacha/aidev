# Research Report: Storacha Platform Technology Specifications (Topics 1-3)

This report covers three foundational technology areas used in the Storacha decentralized storage platform: Content Addressing Fundamentals, CAR & UnixFS, and UCAN & ucanto.

---

## Topic 1: Content Addressing Fundamentals (CID, Multihash, Multicodec, IPLD)

### 1.1 CID (Content Identifier) Specification

**Sources:** [multiformats/cid](https://github.com/multiformats/cid), [IPFS CID docs](https://docs.ipfs.tech/concepts/content-addressing/)

A CID is a self-describing, content-addressed identifier that uses cryptographic hashes to achieve content addressing. CIDs are binary in nature for compactness and are encoded with multibase for text transport.

#### CIDv0 Binary Format

CIDv0 is the legacy format. It consists of **only a multihash** with no explicit version, codec, or multibase identifiers.

```
<CIDv0> ::= <multihash>
```

- Always 34 bytes long (for SHA2-256): leading bytes `[0x12, 0x20, ...]`
- Implicitly assumes:
  - Version: 0
  - Codec: dag-pb (0x70)
  - Hash function: sha2-256 (0x12)
  - Hash digest length: 32 bytes (0x20)
- String representation: Base58btc encoded (always starts with "Qm")
- **No multibase prefix** in the string form (Base58btc is implied)

Detection algorithm: If a binary CID is 34 bytes and starts with `[0x12, 0x20]`, it is CIDv0.

#### CIDv1 Binary Format

CIDv1 is the modern, self-describing format:

```
<CIDv1> ::= <multicodec-cidv1><multicodec-content-type><content-multihash>
```

Broken down:
| Component | Encoding | Description |
|-----------|----------|-------------|
| CID version | unsigned varint | Always `0x01` for CIDv1 |
| Content codec | unsigned varint | Multicodec code (e.g., 0x71 for dag-cbor) |
| Multihash | multihash bytes | Hash function code + digest length + digest |

#### CIDv1 String Format

```
<CIDv1-string> ::= <multibase-prefix><CIDv1-binary-as-encoded>
```

- Default base encoding for CIDv1 strings: **base32lower** (prefix `b`)
- CIDv1 strings typically start with "bafy..." (base32 + CIDv1 marker)

#### CIDv0 to CIDv1 Conversion

CIDv0 can be converted to CIDv1 by prepending:
- Version varint: `0x01`
- Codec varint: `0x70` (dag-pb)

This yields: `<0x01><0x70><original-multihash>`

CIDv1 to CIDv0 conversion is **only possible** when the CIDv1 uses dag-pb (0x70) codec and sha2-256 hash.

#### Key Constants

| Constant | Value | Meaning |
|----------|-------|---------|
| CIDv0 version | (implicit 0) | Legacy, no version byte |
| CIDv1 version | 0x01 | Modern self-describing |
| dag-pb codec | 0x70 | Default CIDv0 codec |
| sha2-256 code | 0x12 | Default CIDv0 hash |
| sha2-256 length | 0x20 (32) | Default CIDv0 digest length |

---

### 1.2 Multihash Specification

**Sources:** [multiformats/multihash](https://github.com/multiformats/multihash), [multiformats.io/multihash](https://multiformats.io/multihash/), [IETF draft-multiformats-multihash-07](https://www.ietf.org/archive/id/draft-multiformats-multihash-07.html)

Multihash is a self-describing hash format using the TLV (type-length-value) pattern.

#### Binary Wire Format

```
<multihash> ::= <hash-func-code><digest-length><digest-value>
```

| Field | Encoding | Description |
|-------|----------|-------------|
| Hash function code | unsigned varint | Identifies the hash function (from multicodec table) |
| Digest length | unsigned varint | Length of the digest in bytes |
| Digest value | raw bytes | The actual hash output, exactly `digest-length` bytes |

#### Construction Algorithm

1. Compute the hash of the content using the chosen hash function.
2. Encode the hash function code as an unsigned varint.
3. Encode the digest length (in bytes) as an unsigned varint.
4. Concatenate: `<hash-func-varint> || <digest-length-varint> || <digest-bytes>`

#### Unsigned Varint Encoding (LEB128)

All varints in multiformats use **unsigned LEB128** with restrictions:
- Serialized 7 bits at a time, starting with least significant bits
- Most significant bit (MSB) of each byte: 1 = more bytes follow, 0 = final byte
- **Must be minimally encoded** (no leading zero bytes)
- Maximum 9 bytes (63 bits of data)

Example: value 300 (0x012C)
- Byte 1: `0xAC` (0b10101100) -- LSB set, 7 data bits: 0101100
- Byte 2: `0x02` (0b00000010) -- MSB clear (final), 7 data bits: 0000010
- Result: `0xAC 0x02`

#### Common Hash Function Codes

| Hash Function | Code | Digest Size (bytes) |
|--------------|------|-------------------|
| identity | 0x00 | variable |
| sha1 | 0x11 | 20 |
| sha2-256 | 0x12 | 32 |
| sha2-512 | 0x13 | 64 |
| sha3-256 | 0x16 | 32 |
| blake2b-256 | 0xb220 | 32 |
| blake3 | 0x1e | 32 |

#### Example: SHA2-256 Multihash

For content hashing to `41dd7b6443542e75701aa98a3c6354d9ddc0fd9e...` (32 bytes):

```
0x12 0x20 0x41dd7b6443542e75701aa98a3c6354d...
^^^^ ^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
|    |    +-- 32 bytes of SHA2-256 digest
|    +------- digest length = 32 (0x20)
+------------ hash function = sha2-256 (0x12)
```

Total: 34 bytes for SHA2-256 multihash.

---

### 1.3 Multicodec Table

**Sources:** [multiformats/multicodec](https://github.com/multiformats/multicodec)

Multicodec is a compact self-describing codec identifier. Each codec is assigned an unsigned varint code from a shared table.

#### Key Codec Codes for IPFS/IPLD

| Name | Code | Tag | Description |
|------|------|-----|-------------|
| identity | 0x00 | multihash | Raw identity (no hashing) |
| sha1 | 0x11 | multihash | SHA-1 hash |
| sha2-256 | 0x12 | multihash | SHA-256 hash |
| sha2-512 | 0x13 | multihash | SHA-512 hash |
| sha3-256 | 0x16 | multihash | SHA3-256 hash |
| raw | 0x55 | ipld | Raw binary, no codec processing |
| dag-pb | 0x70 | ipld | MerkleDAG Protobuf |
| dag-cbor | 0x71 | ipld | MerkleDAG CBOR |
| dag-json | 0x0129 | ipld | MerkleDAG JSON |
| blake2b-256 | 0xb220 | multihash | BLAKE2b-256 hash |

#### Codec Descriptions

- **raw (0x55)**: Pass-through codec. Stored bytes map directly to Data Model Bytes kind. Used for leaf data blocks (e.g., file chunks in UnixFS with raw leaves).
- **dag-pb (0x70)**: The original IPFS file data codec. Uses a fixed Protobuf format to describe connected graphs of named links pointing to file data. Cannot represent the full IPLD Data Model.
- **dag-cbor (0x71)**: The most flexible native IPLD format. Built on CBOR (RFC 8949) with the addition of CBOR tag 42 for CID links. Can represent all Data Model kinds.
- **dag-json (0x0129)**: JSON-based IPLD codec. CID links are encoded as `{"/": "<CID-string>"}`. Bytes are encoded as `{"/": {"bytes": "<base64-data>"}}`.

#### Multibase Prefix Characters

When CIDs are rendered as strings, a multibase prefix identifies the base encoding:

| Encoding | Character | Description |
|----------|-----------|-------------|
| base16 | f | Hexadecimal lowercase |
| base32lower | b | RFC 4648 base32 (default for CIDv1) |
| base36lower | k | Base36 lowercase |
| base58btc | z | Bitcoin Base58 (default for CIDv0) |
| base64 | m | RFC 4648 base64 |
| base64url | u | RFC 4648 base64url |

---

### 1.4 IPLD Data Model Specification

**Sources:** [ipld.io/docs/data-model](https://ipld.io/docs/data-model/), [ipld.io/docs/data-model/kinds](https://ipld.io/docs/data-model/kinds/)

The IPLD Data Model defines the common base types ("kinds") that all IPLD codecs must be able to represent.

#### Scalar Kinds (Terminal Nodes)

| Kind | Cardinality | Description |
|------|-------------|-------------|
| Null | 1 | Only value is `null` |
| Boolean | 2 | `true` or `false` |
| Integer | Infinite | Whole numbers, no fractional component. Min support: at least 2^53 range. No upper bound in spec. |
| Float | Infinite | IEEE 754 double-precision. Use discouraged for content-addressed data due to NaN/precision issues. |
| String | Infinite | Unicode text (UTF-8). No length limit. |
| Bytes | Infinite | Arbitrary byte sequences. No length limit. |

#### Recursive Kinds (Container Nodes)

| Kind | Description |
|------|-------------|
| Map | Ordered collection of key-value pairs. Keys are always Strings. Keys must be unique. Order is preserved. |
| List | Ordered sequence of values. Zero-indexed. |

#### Link Kind (Special)

| Kind | Description |
|------|-------------|
| Link | A CID (Content Identifier) pointing to another block of IPLD data. Scalar in structure but typically transparent during traversal, enabling data graphs that span multiple blocks. |

#### Key Properties

- **Maps preserve insertion order** -- iteration order is defined and stable.
- **Map keys are always strings** -- unlike some languages' map types.
- **No undefined/missing values** -- every key in a map has a value; absence of a key means the entry does not exist.
- **Links are opaque** -- the Data Model treats Links as values; resolution/traversal is a layer above.

#### Codec Mapping

Each codec defines how Data Model kinds map to its serialization format:
- **DAG-CBOR**: All kinds supported natively. Links encoded with CBOR tag 42.
- **DAG-PB**: Only supports a subset (Map with "Data" bytes and "Links" list). Cannot represent arbitrary Data Model structures.
- **DAG-JSON**: All kinds supported. Links represented as `{"/": "CID-string"}`. Bytes as `{"/": {"bytes": "base64"}}`.
- **Raw**: Only Bytes kind.

---

### 1.5 DAG-CBOR Specification

**Sources:** [ipld.io/specs/codecs/dag-cbor/spec](https://ipld.io/specs/codecs/dag-cbor/spec/)

DAG-CBOR is a strict subset of CBOR (RFC 8949) with deterministic encoding rules.

#### Link Encoding (Tag 42)

CID links in DAG-CBOR are encoded as:
1. CBOR tag 42 header: `0xd82a` (major type 6 with 8-bit integer 42)
2. CBOR byte string (major type 2) containing:
   - `0x00` (identity multibase prefix, required for historical reasons)
   - CID in binary form

```
0xd82a <CBOR-byte-string(0x00 || CID-binary)>
```

#### Deterministic Encoding Rules

- Map keys MUST be sorted by byte value (shortest first, then lexicographic)
- Only CBOR tag 42 is permitted
- Integer encoding MUST use the smallest possible CBOR representation
- Floating-point values MUST use the smallest lossless encoding (float16 if possible, then float32, then float64)
- No indefinite-length encoding allowed

---

### 1.6 IPLD Schemas

**Sources:** [ipld.io/docs/schemas/intro](https://ipld.io/docs/schemas/intro/), [ipld.io/docs/schemas/features/typekinds](https://ipld.io/docs/schemas/features/typekinds/), [ipld.io/docs/schemas/features/representation-strategies](https://ipld.io/docs/schemas/features/representation-strategies/)

IPLD Schemas provide a type layer on top of the Data Model for validation, documentation, and code generation.

#### Type Kinds

Schemas support all Data Model kinds plus additional type kinds:

| Type Kind | Maps to DM Kind | Description |
|-----------|-----------------|-------------|
| Bool | Boolean | Boolean type |
| Int | Integer | Integer type |
| Float | Float | Float type |
| String | String | String type |
| Bytes | Bytes | Byte sequence type |
| Map | Map | Typed key-value collection |
| List | List | Typed ordered sequence |
| Link | Link | CID reference (optionally typed: `&TargetType`) |
| Struct | Map (default) | Named fields with types |
| Union | (varies) | Sum/variant type (tagged, kinded, envelope, inline, byteprefix) |
| Enum | String (default) | Named constants |
| Copy | (matches source) | Type alias |
| Any | (any kind) | Unconstrained type |

#### Struct Representation Strategies

- **map** (default): Fields become Map keys. Field names are keys, values are typed.
- **tuple**: Fields packed into a List (ordered, no keys). Very compact.
- **stringjoin**: Fields concatenated into a single String with a delimiter.
- **listpairs**: Like map but serialized as `[[key, value], [key, value], ...]`.

Example:
```ipldsch
type MyStruct struct {
  name String
  age  Int
} representation tuple
```

#### Union Representation Strategies

- **keyed**: Discriminated by a map key. `{ "typeA": <value> }` or `{ "typeB": <value> }`.
- **kinded**: Discriminated by the Data Model kind itself (e.g., string vs map).
- **envelope**: Wrapped in a map with a discriminant key and a content key.
- **inline**: Discriminant key pulled up into the map alongside other fields.
- **byteprefix**: Binary discrimination by a leading byte.

#### Enum Representation

- **string** (default): Enum members map to string values.
- **int**: Enum members map to integer values.

#### Advanced Data Layouts (ADLs)

ADLs are plugins that present a synthesized view of underlying data:
- **HAMT (HashMap)**: Multi-block key/value storage using a hash array mapped trie.
- **Flexible Byte Layout (FBL)**: Multi-block binary data representation.
- ADLs can span multiple blocks transparently.
- ADLs have a "synthesized" view (single Node) and a "substrate" (actual serialized data).

---

## Topic 2: CAR & UnixFS

### 2.1 CARv1 Format Specification

**Sources:** [ipld.io/specs/transport/car/carv1](https://ipld.io/specs/transport/car/carv1/)

CAR (Content Addressable aRchive) is a serialized representation of any IPLD DAG as a concatenation of its blocks, plus a header.

#### Overall Structure

```
CARv1 = <header-varint><header-DAG-CBOR> [<block-varint><block-CID><block-data>]*
```

#### Header Format

The header is the first entry in the CAR file:

1. **Length prefix**: unsigned varint specifying the number of bytes in the header block (NOT including the varint itself).
2. **Header block**: DAG-CBOR encoded map with the following IPLD Schema:

```ipldsch
type CarHeader struct {
  version  Int      -- MUST be 1
  roots    [&Any]   -- One or more root CIDs
}
```

DAG-CBOR representation:
```cbor
{
  "version": 1,
  "roots": [CID, CID, ...]
}
```

The `roots` array MUST contain one or more CIDs. Each root CID SHOULD be present somewhere in the data section.

#### Block Entry Format

After the header, each block is encoded as:

```
<entry> ::= <varint-length><CID><block-data>
```

| Component | Encoding | Description |
|-----------|----------|-------------|
| Length | unsigned varint | Total bytes of CID + block-data (excludes the varint itself) |
| CID | binary CID | The content identifier for this block |
| Block data | raw bytes | The serialized block content (length = total - CID byte length) |

#### Construction Algorithm

1. Encode the header as DAG-CBOR: `{"version": 1, "roots": [<root-CID-1>, ...]}`
2. Compute the byte length of the header, encode as unsigned varint.
3. Write: `<header-length-varint><header-bytes>`
4. For each block in the DAG:
   a. Serialize the block content according to its codec.
   b. Compute CID for the block (codec + multihash of content).
   c. Compute total byte length of CID binary + block content.
   d. Write: `<total-length-varint><CID-bytes><block-content-bytes>`

#### Key Properties

- Blocks MAY appear in any order (no ordering requirement).
- Duplicate blocks MAY appear.
- Not all blocks referenced by CIDs in the archive need to be present (sparse DAGs allowed).
- The codec in each block's CID indicates how to decode the block data.

---

### 2.2 CARv2 Format Specification

**Sources:** [ipld.io/specs/transport/car/carv2](https://ipld.io/specs/transport/car/carv2/)

CARv2 wraps a CARv1 payload with a pragma, header, and optional index for random access.

#### Overall Structure

```
CARv2 = <11-byte pragma><40-byte header>[padding]<CARv1 payload>[padding][index]
```

#### Pragma (11 bytes, fixed)

```
0x0a a16776657273696f6e02
```

Breakdown:
- `0x0a` = varint(10), indicating 10 bytes of header follow (mimics a CARv1 header length prefix)
- `a16776657273696f6e02` = CBOR encoding of `{"version": 2}`

This pragma is designed so that a CARv1 reader encountering a CARv2 file will read it as a CARv1 header with `version: 2` and can reject or handle it gracefully.

#### Header (40 bytes, fixed, little-endian)

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 16 | Characteristics | 128-bit bitfield | Feature flags |
| 16 | 8 | Data offset | uint64 LE | Byte offset to CARv1 data payload from start of file |
| 24 | 8 | Data size | uint64 LE | Byte length of CARv1 data payload |
| 32 | 8 | Index offset | uint64 LE | Byte offset to index payload (0 = no index) |

#### Characteristics Bitfield

- **Bit 0** (leftmost): "Fully indexed" -- when set (1), the index MUST include a complete catalog of all block CIDs in the data payload.
- All other bits are reserved and MUST be 0.

#### Index Format

The index begins at the byte offset specified in the header's "Index offset" field.

```
<index> ::= <codec-varint><index-data>
```

The first varint identifies the index format:

| Index Codec | Code | Description |
|-------------|------|-------------|
| IndexSorted | 0x0400 | Sorted list of multihash-digest + offset pairs |
| MultihashIndexSorted | 0x0401 | Grouped by multihash code, then sorted digests + offsets |

**IndexSorted (0x0400) format:**
- Width (uint32 LE): byte width of each record (digest + uint64 offset)
- Count (uint64 LE): number of records
- Records: sorted by digest, each record = `<digest-bytes><uint64-LE-offset>`

**MultihashIndexSorted (0x0401) format:**
- Count (int32 LE): number of multicodec groups
- For each group:
  - Multicodec code (varint): hash function code
  - IndexSorted: an IndexSorted index for that hash function

#### Padding

Optional zero-byte padding may appear between the header and CARv1 payload, and between the CARv1 payload and the index. This allows for alignment optimization.

---

### 2.3 UnixFS Specification

**Sources:** [specs.ipfs.tech/unixfs](https://specs.ipfs.tech/unixfs/), [go-unixfs/pb/unixfs.proto](https://github.com/ipfs/go-unixfs/blob/master/pb/unixfs.proto)

UnixFS is the data format used to represent files, directories, and symlinks in IPFS. It is encoded as a Protobuf message stored inside DAG-PB nodes.

#### Protobuf Schema

```protobuf
message Data {
  enum DataType {
    Raw       = 0;
    Directory = 1;
    File      = 2;
    Metadata  = 3;
    Symlink   = 4;
    HAMTShard = 5;
  }

  required DataType Type = 1;
  optional bytes     Data = 2;
  optional uint64    filesize = 3;
  repeated uint64    blocksizes = 4;
  optional uint64    hashType = 5;
  optional uint64    fanout = 6;
  optional uint32    mode = 7;      // UnixFS 1.5
  optional UnixTime  mtime = 8;     // UnixFS 1.5
}

message UnixTime {
  required int64  Seconds = 1;
  optional fixed32 FractionalNanoseconds = 2;
}
```

#### Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| Type | Yes | Enum identifying the node type |
| Data | Conditional | File content (for leaves), symlink target, HAMT bitmap |
| filesize | For File/Raw | Total size of the file content in bytes |
| blocksizes | For multi-block File | Size of each child block's content |
| hashType | For HAMTShard | Hash function for HAMT (murmur3-x64-64) |
| fanout | For HAMTShard | HAMT table width (power of 2, max 1024) |
| mode | Optional (v1.5) | Unix file mode bits |
| mtime | Optional (v1.5) | Last modification time |

#### File Chunking Strategies

Files are split into chunks before being organized into a DAG:

**Fixed-size chunking (default):**
- Default chunk size: **262,144 bytes (256 KiB)**
- Simple: splits file at fixed byte boundaries
- Deterministic but poor deduplication across similar files

**Rabin fingerprint chunking:**
- Content-defined chunking using Rabin fingerprinting
- Chunk boundaries depend on content, not position
- Better deduplication: if middle of file changes, only affected chunks differ
- Parameters: average chunk size, min chunk size, max chunk size

**Buzhash chunking:**
- Another content-defined chunking approach
- Uses a rolling hash (buzhash) to find chunk boundaries

#### Layout Strategies

After chunking, chunks are organized into a Merkle DAG:

**Balanced layout (default):**
1. Take up to `max-width` (default: 174) chunks from the chunk stream.
2. Create a UnixFS File node linking to all of them.
3. Repeat until `max-width` intermediate nodes are created.
4. Create a parent node linking to the intermediate nodes.
5. Continue recursively until a single root node is reached.

**Trickle layout:**
- Optimized for streaming/sequential access.
- Builds a DAG that prioritizes depth-first access patterns.

#### Leaf Formats

- **UnixFS leaves**: Chunk data wrapped in a UnixFS Data protobuf, then in a DAG-PB node. CID codec = dag-pb (0x70).
- **Raw leaves** (recommended): Chunk data stored as raw bytes with CID codec = raw (0x55). More efficient and produces canonical CIDs for single-block files.

#### Block Size Constraints

- Recommended new block sizes: **256 KiB** (legacy) or **1 MiB** (modern maximum recommended)
- Implementations MUST decode blocks up to **2 MiB**
- The 174 max-width default comes from: floor(256 KiB / max-link-overhead) where each link is ~46 bytes (34 byte CID + name + Tsize)

#### Directory Types

**Basic Directory:**
- A DAG-PB node with UnixFS Data of Type=Directory
- Child entries are DAG-PB links with names set to filenames
- Each link points to the child's root CID

**HAMT-Sharded Directory (for large directories):**
- When directory entries exceed a threshold, a HAMT (Hash Array Mapped Trie) is used
- UnixFS Data with Type=HAMTShard
- hashType field set to murmur3-x64-64
- fanout: HAMT table width (typically 256)
- Data field contains the bitmap indicating which buckets are occupied
- Link names are hex-encoded bucket indices concatenated with the entry name

---

### 2.4 DAG-PB Specification

**Sources:** [ipld.io/specs/codecs/dag-pb/spec](https://ipld.io/specs/codecs/dag-pb/spec/), [ipld/specs/codecs/dag-pb](https://github.com/ipld/ipld/blob/master/specs/codecs/dag-pb/spec.md)

DAG-PB is a Protobuf-based IPLD codec that encodes a byte array and an associated list of links.

#### Protobuf Schema

```protobuf
message PBLink {
  optional bytes  Hash  = 1;  // Binary CID of target (no multibase prefix)
  optional string Name  = 2;  // UTF-8 string name
  optional uint64 Tsize = 3;  // Cumulative size of target object
}

message PBNode {
  optional bytes       Data  = 1;  // Opaque user data (e.g., UnixFS protobuf)
  repeated PBLink      Links = 2;  // References to other objects
}
```

#### Wire Format Details

Protobuf wire types used:
- `bytes` fields: wire type 2 (length-delimited)
- `string` fields: wire type 2 (length-delimited)
- `uint64` fields: wire type 0 (varint)

Field tag encoding: `(field_number << 3) | wire_type`

| Field | Tag Byte | Description |
|-------|----------|-------------|
| PBNode.Data | 0x0a | field 1, wire type 2 |
| PBNode.Links | 0x12 | field 2, wire type 2 |
| PBLink.Hash | 0x0a | field 1, wire type 2 |
| PBLink.Name | 0x12 | field 2, wire type 2 |
| PBLink.Tsize | 0x18 | field 3, wire type 0 |

#### Canonical Form Requirements

1. PBLink fields MUST appear in field-number order: Hash (1), Name (2), Tsize (3).
2. PBNode fields: Links (2) entries appear BEFORE Data (1) in the binary encoding. This is because PBNode.Links is field 2 and PBNode.Data is field 1, but the canonical ordering requires Links first (this is a historical quirk of the dag-pb format -- Links are sorted and placed first).
3. Links MUST be sorted by Name (lexicographic byte comparison). If Names are equal, sort by Hash.
4. Blocks with out-of-order PBLink fields SHOULD be rejected.
5. Only defined fields may appear -- extra fields are invalid.

#### IPLD Data Model Mapping

DAG-PB maps to the IPLD Data Model as:

```
PBNode -> Map {
  "Data"  -> Bytes (optional)
  "Links" -> List [
    Map {
      "Hash"  -> Link (CID)
      "Name"  -> String (optional)
      "Tsize" -> Int (optional)
    },
    ...
  ]
}
```

#### Merkle Linking

- The `Hash` field in PBLink contains a **binary CID** (no multibase prefix).
- This CID references another DAG-PB block (or raw block) forming the Merkle DAG.
- `Tsize` is the cumulative size of the linked subtree (block data + all descendant data), used for size estimation without traversal.

---

## Topic 3: UCAN & ucanto

### 3.1 UCAN Specification

**Sources:** [ucan-wg/spec](https://github.com/ucan-wg/spec), [ucan.xyz/specification](https://ucan.xyz/specification/), [Storacha UCAN docs](https://docs.storacha.network/concepts/ucan/)

UCAN (User Controlled Authorization Network) is a trustless, secure, local-first, user-originated authorization and revocation scheme. It extends JWT structure for delegable, public-key-verifiable capabilities.

#### Token Structure

UCANs are formatted as JWTs with three base64url-encoded sections separated by dots:

```
<base64url(header)>.<base64url(payload)>.<base64url(signature)>
```

#### Header Fields

```json
{
  "alg": "EdDSA",       // Signing algorithm (REQUIRED)
  "typ": "JWT",          // Token type (REQUIRED, always "JWT")
  "ucv": "0.10.0"        // UCAN spec version (REQUIRED)
}
```

Supported algorithms:
- **EdDSA** (Ed25519) -- most common in Storacha
- **ES256** (NIST P-256/secp256r1)
- **ES256K** (secp256k1)
- **RS256** (RSA with SHA-256)

#### Payload Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `iss` | Yes | DID string | Issuer -- DID of the signing principal |
| `aud` | Yes | DID string | Audience -- DID of the intended recipient |
| `exp` | Yes | Integer/null | Expiration -- Unix timestamp, or `null` for no expiry |
| `nbf` | No | Integer | Not Before -- Unix timestamp for validity start |
| `nnc` | No | String | Nonce -- random value for uniqueness |
| `att` | Yes | Array | Attenuations -- array of capabilities being delegated |
| `prf` | Yes | Array | Proofs -- array of CID strings referencing parent UCANs |
| `fct` | No | Array | Facts -- arbitrary assertions (not delegated) |

#### Capability Format

Each entry in the `att` (attenuations) array:

```json
{
  "with": "did:key:z6Mkk89b...",    // Resource URI
  "can": "store/add",                // Ability string
  "nb": {                            // Caveats (optional constraints)
    "size": 1048576,
    "link": { "/": "bafy..." }
  }
}
```

**Resource (`with`):** A URI identifying the resource. Common patterns:
- `did:key:z6Mk...` -- a DID-identified space/account
- `did:web:example.com` -- a web-based DID
- `file:///path/to/resource` -- a file resource

**Ability (`can`):** A namespaced action string in the format `<namespace>/<action>` or `*` (all abilities). Examples:
- `store/add`, `store/remove`, `store/list`
- `upload/add`, `upload/remove`, `upload/list`
- `space/info`, `space/recover`
- `*` -- wildcard, all abilities

**Caveats (`nb`):** Optional constraints that narrow the scope. Must be equal to or more restrictive than the parent delegation.

#### UCAN IPLD Representation (DAG-CBOR)

Modern UCANs (as used in Storacha/ucanto) are encoded as DAG-CBOR with this structure:

```ipldsch
type UCAN struct {
  v     String          -- version string (e.g., "0.9.1")
  iss   DID             -- issuer DID
  aud   DID             -- audience DID
  s     Signature       -- cryptographic signature
  att   [Capability]    -- attenuations (capabilities)
  prf   [&UCAN]         -- proofs (CID links to parent UCANs)
  exp   nullable Int    -- expiration timestamp (null = no expiry)
  fct   [Fact]          -- facts
  nnc   optional String -- nonce
  nbf   optional Int    -- not before timestamp
}

type Capability struct {
  with  String          -- resource URI
  can   String          -- ability
  nb    {String: Any}   -- caveats
}
```

The UCAN envelope tag: `ucan/dlg@1.0.0-rc.1`

Signature is computed over the canonical DAG-CBOR encoding of the payload (or JWT form for JWT UCANs).

#### Delegation Semantics

**Delegation chain:** A linked sequence of UCANs where each UCAN's `aud` matches the next UCAN's `iss`.

```
Root UCAN:     iss=Alice, aud=Bob,   att=[store/*]
  |
  v (Bob delegates to Carol)
Child UCAN:    iss=Bob,   aud=Carol, att=[store/add], prf=[CID-of-root]
  |
  v (Carol invokes)
Invocation:    iss=Carol, aud=Service, att=[store/add], prf=[CID-of-child]
```

**Attenuation rule:** Each delegation MUST either directly restate or attenuate (narrow) its parent's capabilities. You cannot escalate -- only maintain or reduce scope.

**Proof Validation Algorithm:**

1. Parse the UCAN token (JWT or DAG-CBOR).
2. Verify the signature against the `iss` public key.
3. Check time bounds: `nbf <= now <= exp`.
4. Check the nonce is not reused (if applicable).
5. For each capability in `att`:
   a. If `prf` is empty, the `iss` must be the resource owner (self-issued).
   b. For each proof CID in `prf`:
      - Load and parse the referenced UCAN.
      - Verify its `aud` matches this UCAN's `iss`.
      - Recursively validate the proof UCAN (steps 1-5).
      - Check that the claimed capability is attenuated from a capability in the proof.
6. Check revocation status.

#### Key Terminology

| Term | Definition |
|------|-----------|
| **Issuer (iss)** | The principal signing and creating the UCAN. Their DID appears in the `iss` field. |
| **Audience (aud)** | The principal to whom the UCAN is addressed. Their DID appears in the `aud` field. |
| **Principal** | Any entity with a DID that can participate in UCAN flows. |
| **Capability** | A `{with, can, nb}` triple describing a permitted action on a resource. |
| **Resource** | The `with` field -- a URI identifying what is being acted upon. |
| **Ability** | The `can` field -- a string describing the action permitted. |
| **Caveats** | The `nb` field -- optional constraints narrowing the capability. |
| **Delegation** | The act of creating a new UCAN granting capabilities to another principal. |
| **Attenuation** | Narrowing capabilities in a delegation (cannot escalate). |
| **Proof** | A reference (CID) to a parent UCAN that grants authority for the current UCAN. |
| **Invocation** | Exercising a capability to perform an action. |
| **Authority** | A trusted DID identifier (e.g., the service). |
| **Verifier** | The subsystem that validates UCAN chains. |

---

### 3.2 UCAN Invocation Specification

**Sources:** [ucan-wg/invocation](https://github.com/ucan-wg/invocation), [Storacha specs/w3-ucan.md](https://github.com/storacha/specs/blob/main/w3-ucan.md)

UCAN Invocation defines the format for expressing the intention to execute delegated capabilities and the receipts from execution.

#### Invocation Structure

An Invocation is a UCAN token that exercises a capability:

```ipldsch
type Invocation struct {
  v     String          -- UCAN version
  iss   DID             -- invoker's DID
  aud   DID             -- executor's DID (the service)
  s     Signature       -- invoker's signature
  att   [Capability]    -- the capability being invoked (typically one)
  prf   [&UCAN]         -- proof chain from subject to invoker
  exp   nullable Int    -- expiration
  nnc   String          -- REQUIRED nonce for uniqueness (non-idempotent)
  nbf   optional Int    -- not before
  cause optional &Receipt -- provenance: which receipt triggered this invocation
}
```

The `prf` field MUST be an array of CIDs pointing to Delegations in strict sequence:
- Starting from the root Delegation (issued by the Subject/resource owner)
- The `aud` of each delegation matches the `iss` of the next
- Ending with a delegation whose `aud` matches the Invoker's DID

#### Task Structure

A Task is the subset of Invocation fields that uniquely determine the work to be performed:

```ipldsch
type Task struct {
  can   String          -- ability to invoke
  with  String          -- resource URI
  nb    {String: Any}   -- caveats/arguments
}
```

Tasks are the "pure" description of work, independent of authorization.

#### Receipt Structure

A Receipt is the attested result of an invocation:

```ipldsch
type Receipt struct {
  iss   DID             -- receipt issuer (the executor)
  ran   &Invocation     -- CID link to the invocation this receipt is for
  out   Result          -- the result of execution
  fx    Effects         -- side effects / follow-up tasks
  meta  {String: Any}   -- arbitrary metadata (job IDs, fuel used, etc.)
  prf   [&UCAN]         -- proof chain for the receipt
  s     Signature       -- executor's signature
}

type Result union {
  | Any           "ok"      -- success value
  | {String: Any} "error"   -- error value with message and details
} representation keyed

type Effects struct {
  fork [&Task]            -- tasks that can run concurrently
  join optional &Task     -- task that must wait for forks to complete
}
```

#### Result Format

Results use a discriminated union:
- **Success:** `{"ok": <any-value>}`
- **Error:** `{"error": {"name": "...", "message": "...", ...}}`

#### Effect Declarations

Receipts can request additional work via the `fx` field:
- `fork`: Array of Task CIDs that can be enqueued for concurrent execution.
- `join`: Optional Task CID that should execute after all forks complete.

This enables **pipelining** -- chaining invocations where the output of one feeds into the next.

#### Storacha Extensions: Attestation, Revocation, Conclusion

From `specs/w3-ucan.md`:

**ucan/attest** -- Allows an authority to attest that a UCAN delegation chain is valid (cached verification):
```ipldsch
type Attest struct {
  with   Authority      -- DID of the attesting authority
  nb     Attestation    -- { proof: &UCAN }
}
```

**ucan/revoke** -- Revoke a UCAN delegation:
```ipldsch
type Revoke struct {
  with   Authority      -- DID of the revoking principal
  nb     Revocation     -- { ucan: &UCAN, proof: [&UCAN] }
}
```

**ucan/conclude** -- Represent a receipt as a UCAN capability (enables delegation of receipt-issuing):
```ipldsch
type Conclude struct {
  with   Authority
  nb     Conclusion     -- { ran: &Invocation, out: Result, next: [&Task], meta: Meta, time: Int }
}
```

---

### 3.3 ucanto Framework

**Sources:** [storacha/ucanto](https://github.com/storacha/ucanto), local README files in `ucanto/`

ucanto is a TypeScript library for UCAN-based RPC. It provides a complete framework for defining, invoking, validating, and executing UCAN capabilities.

#### Architecture Overview

ucanto provides six core packages:

| Package | Role |
|---------|------|
| `@ucanto/core` | Foundational capability definition, validation, and invocation primitives |
| `@ucanto/server` | UCAN-based RPC server with capability routing and authorization |
| `@ucanto/client` | Client for creating, signing, and sending UCAN invocations |
| `@ucanto/transport` | Pluggable encoding (CAR, CBOR) and transport (HTTP) layer |
| `@ucanto/principal` | Cryptographic identity management (Ed25519, key generation/parsing) |
| `@ucanto/validator` | UCAN validation and proof chain verification |
| `@ucanto/interface` | Shared TypeScript type definitions and contracts |

#### Capability Definition

Capabilities are defined declaratively using the `capability()` function from `@ucanto/core`:

```ts
import { capability, URI, Link, Schema } from '@ucanto/core'

const StoreAdd = capability({
  can: 'store/add',                          // Ability string
  with: URI.match({ protocol: 'did:' }),     // Resource constraint
  nb: Schema.struct({                        // Caveat schema
    link: Link,                              // Must be a CID
    size: Schema.integer().optional(),       // Optional integer
  }),
  derives: (claimed, delegated) => {         // Attenuation check
    if (claimed.with !== delegated.with) {
      return new Failure('Resource mismatch')
    }
    return { ok: {} }
  }
})
```

Key elements:
- `can`: The ability string (namespace/action format)
- `with`: URI matcher constraining valid resource URIs
- `nb`: Schema for caveats -- validates invocation parameters
- `derives`: Custom function to check if a claimed capability derives from a delegated one (attenuation logic)

#### Server Creation

```ts
import * as Server from '@ucanto/server'
import * as CAR from '@ucanto/transport/car'
import { ed25519 } from '@ucanto/principal'

// Define a handler for a capability
const storeAdd = Server.provide(StoreAdd, async ({ capability, invocation }) => {
  // capability.with = resource URI
  // capability.nb = validated caveats
  return { status: 'ok', link: capability.nb.link }
})

// Create the server
const server = Server.create({
  id: ed25519.parse(SERVICE_SECRET_KEY),     // Server's signing identity
  service: {
    store: { add: storeAdd }                  // Route: store/add -> handler
  },
  codec: CAR.inbound,                         // Decode incoming CAR, encode outgoing CAR
  canIssue: (capability, issuer) => {         // Custom authorization check
    // Return true if issuer can self-issue this capability
    return capability.with === issuer
  }
})
```

The service object structure mirrors the ability namespace: `store/add` maps to `service.store.add`.

#### Client Usage

```ts
import * as Client from '@ucanto/client'
import * as HTTP from '@ucanto/transport/http'
import { CAR } from '@ucanto/transport'

// Create a connection to the service
const connection = Client.connect({
  id: serviceDID,                             // Service's public DID
  codec: CAR.outbound,                        // Encode requests as CAR
  channel: HTTP.open({                        // HTTP transport channel
    url: new URL('https://api.example.com')
  })
})

// Create and execute an invocation
const invocation = Client.invoke({
  issuer: agentKey,           // Client's signing key
  audience: serviceDID,       // Service DID
  capability: {
    can: 'store/add',
    with: agentKey.did(),
    nb: { link: someCID }
  },
  proofs: [delegation]        // Optional proof chain
})

const receipt = await invocation.execute(connection)
// receipt.out.ok or receipt.out.error
```

#### Delegation

```ts
const delegation = await Client.delegate({
  issuer: alice,              // Delegator (must have the capability)
  audience: bob,              // Recipient
  capabilities: [{
    can: 'store/add',
    with: alice.did(),        // Resource
  }],
  expiration: Math.floor(Date.now() / 1000) + 3600,  // 1 hour
  proofs: [aliceProof]        // Alice's proof of authority
})
```

#### Transport Layer

Transport handles serialization and network communication:

- **CAR encoding**: UCAN invocations are packaged as CAR files containing:
  - The invocation UCAN(s) as DAG-CBOR blocks
  - All referenced delegation UCANs as blocks
  - The proof chain blocks
- **Content types**: `application/vnd.ipld.car`
- **Pluggable codecs**: Both inbound (server-side decode) and outbound (client-side encode)

```ts
import { Codec, CAR } from '@ucanto/transport'

// Client-side codec
const outbound = Codec.outbound({
  encoders: { 'application/vnd.ipld.car': CAR.request },
  decoders: { 'application/vnd.ipld.car': CAR.response },
})

// Server-side codec
const inbound = Codec.inbound({
  decoders: { 'application/vnd.ipld.car': CAR.request },
  encoders: { 'application/vnd.ipld.car': CAR.response },
})
```

#### Batch Invocations

Multiple invocations can be sent in a single request:

```ts
const [result1, result2] = await connection.execute([invocation1, invocation2])
```

The transport layer packages multiple invocations into a single CAR file and the server processes them, returning receipts for each.

#### Validation Flow

When the server receives an invocation:

1. **Decode**: Transport layer decodes the CAR file, extracting invocations and delegation blocks.
2. **Reassemble proofs**: Delegation CIDs are resolved from the CAR blocks back into a chain.
3. **Validate signatures**: Each UCAN in the chain is verified against its issuer's public key.
4. **Check chain alignment**: `aud` of each UCAN matches `iss` of the next.
5. **Check time bounds**: All UCANs in the chain must be within their valid time window.
6. **Check attenuation**: The invoked capability must derive from the capabilities in the proof chain.
7. **Check authorization**: The `canIssue` function (if provided) validates self-issued capabilities.
8. **Route and execute**: The capability is routed to the matching handler via the service object.
9. **Return receipt**: The handler's result is wrapped in a signed Receipt and sent back.

#### Principal Management

```ts
import { ed25519 } from '@ucanto/principal'

// Generate new Ed25519 keypair
const agent = await ed25519.generate()

// Serialize private key for storage
const serialized = ed25519.format(agent)  // Base64 string starting with "Mg.."

// Deserialize from stored key
const restored = ed25519.parse(serialized)

// Get the public DID
const did = agent.did()  // "did:key:z6Mk..."
```

Key types:
- **Signer**: Has private key, can sign UCANs. Implements `{ did(), sign(payload) }`.
- **Verifier**: Has only public key, can verify signatures. Implements `{ did(), verify(payload, sig) }`.

#### Connection to Storacha

Storacha's service endpoints:
- Service DID: `did:web:up.storacha.network`
- Service URL: `https://up.storacha.network`

The entire Storacha w3up API is implemented as ucanto capabilities (e.g., `store/add`, `upload/add`, `space/info`), making every API call a UCAN invocation with full delegation chain support.

---

## Summary of Key Relationships

### How These Technologies Connect in Storacha

1. **Content is chunked** using UnixFS chunking strategies (default 256 KiB fixed-size).
2. **Chunks become blocks** -- each chunk is hashed (SHA2-256) to produce a **Multihash**, combined with a codec identifier to form a **CID**.
3. **Blocks are organized** into a Merkle DAG using **DAG-PB** (for UnixFS file trees) or **DAG-CBOR** (for structured data).
4. **DAGs are serialized** into **CAR files** (CARv1 for transport, CARv2 for indexed storage).
5. **Uploads are authorized** via **UCAN** delegations -- a user delegates `store/add` capability to their agent.
6. **The agent invokes** `store/add` via **ucanto** RPC, sending the CAR file in the request body.
7. **The server validates** the UCAN proof chain, processes the invocation, stores the CAR, and returns a signed Receipt.
8. **All references** between blocks, invocations, delegations, and receipts are **CID links** -- making the entire system content-addressed and verifiable.

---

## References

### Topic 1: Content Addressing
- [CID Specification](https://github.com/multiformats/cid)
- [Multihash Specification](https://multiformats.io/multihash/)
- [IETF Multihash Draft](https://www.ietf.org/archive/id/draft-multiformats-multihash-07.html)
- [Multicodec Table](https://github.com/multiformats/multicodec)
- [Multibase Specification](https://github.com/multiformats/multibase)
- [Unsigned Varint Specification](https://github.com/multiformats/unsigned-varint)
- [IPLD Data Model](https://ipld.io/docs/data-model/)
- [IPLD Data Model Kinds](https://ipld.io/docs/data-model/kinds/)
- [IPLD Schemas Introduction](https://ipld.io/docs/schemas/intro/)
- [IPLD Schemas Representation Strategies](https://ipld.io/docs/schemas/features/representation-strategies/)
- [IPLD Advanced Data Layouts](https://ipld.io/docs/advanced-data-layouts/)
- [DAG-CBOR Specification](https://ipld.io/specs/codecs/dag-cbor/spec/)
- [IPLD Specs Repository](https://github.com/ipld/specs)

### Topic 2: CAR & UnixFS
- [CARv1 Specification](https://ipld.io/specs/transport/car/carv1/)
- [CARv2 Specification](https://ipld.io/specs/transport/car/carv2/)
- [UnixFS Specification](https://specs.ipfs.tech/unixfs/)
- [UnixFS Protobuf Definition](https://github.com/ipfs/go-unixfs/blob/master/pb/unixfs.proto)
- [DAG-PB Specification](https://ipld.io/specs/codecs/dag-pb/spec/)
- [DAG-PB JavaScript Implementation](https://github.com/ipld/js-dag-pb)

### Topic 3: UCAN & ucanto
- [UCAN Specification](https://github.com/ucan-wg/spec)
- [UCAN Specification Website](https://ucan.xyz/specification/)
- [UCAN Invocation Specification](https://github.com/ucan-wg/invocation)
- [UCAN IPLD Schema](https://github.com/ucan-wg/ucan-ipld)
- [UCAN Delegation Specification](https://github.com/ucan-wg/delegation)
- [ucanto Repository](https://github.com/storacha/ucanto)
- [Storacha UCAN Concepts](https://docs.storacha.network/concepts/ucan/)
- [UCANs and Storacha](https://docs.storacha.network/concepts/ucans-and-storacha/)
- [Storacha W3 UCAN Extensions](https://github.com/storacha/specs/blob/main/w3-ucan.md)
- [IPLD DAG-UCAN Codec](https://github.com/ipld/js-dag-ucan)
