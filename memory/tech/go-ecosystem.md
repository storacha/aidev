<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Go Ecosystem: Patterns & Reference

> **TL;DR:** Go services use `go-ucanto` for UCAN RPC (mirrors JS ucanto: `server.NewServer` + `server.Provide` + `server.WithServiceMethod`) and `go-libstoracha` for capability definitions (blob, assert, pdp, etc.). IPLD data uses `bindnode` with schema strings. Key services: Piri (Cobra/Viper, uber/fx, Lambda), Indexing Service (urfave/cli, Echo), Etracker (Cobra). All Go modules under `github.com/storacha/*`. No DHT -- content routing via IPNI HTTP API.

> Concepts: go-ucanto server/handler (P0), go-libstoracha capabilities (P0), go-ipld-prime (P0), go-cid (P1), service entry points (P1)
> Key repos: go-ucanto, go-libstoracha, go-cid, go-ipld-prime, indexing-service, piri

## Go Service Architecture

```
                   indexing-service                              piri
                   (urfave/cli)                                  (cobra/viper)
                        │                                             │
                        ├── ed25519.Parse(key) → Signer              ├── cobra commands: serve, wallet, identity
                        ├── construct.Construct(cfg) → Service        ├── aws.Construct(cfg) → Service
                        ├── server.ListenAndServe(addr, svc, opts)   ├── Lambda: lambda.StartHTTPHandler
                        │                                             │
                        └── go-ucanto Server                         └── go-ucanto Server
                              │                                             │
                              ├── server.NewServer(signer, opts...)         ├── server.NewServer(signer, opts...)
                              ├── server.WithServiceMethod(can, handler)    ├── server.WithServiceMethod(can, handler)
                              └── server.Provide(cap, fn)                   └── server.Provide(cap, fn)
                                    │                                             │
                                    └── go-libstoracha capabilities              └── go-libstoracha capabilities
```

## Patterns

### Pattern: Create a go-ucanto server
**When:** Building a Go service that handles UCAN invocations
**Template:**
```go
import (
    "github.com/storacha/go-ucanto/principal/ed25519"
    "github.com/storacha/go-ucanto/server"
)

// Parse identity
id, err := ed25519.Parse(privateKeyString)

// Create server with capability handlers
srv, err := server.NewServer(
    id,
    server.WithServiceMethod(
        "blob/allocate",
        server.Provide(blob.Allocate, handleBlobAllocate),
    ),
    server.WithServiceMethod(
        "blob/accept",
        server.Provide(blob.Accept, handleBlobAccept),
    ),
)

// Wire to HTTP
http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
    res, err := srv.Request(r.Context(), uhttp.NewHTTPRequest(r.Body, r.Header))
    // write response...
})
```
**Key files:** `go-ucanto/server/server.go`
**Gotchas:**
- `Service` is `map[ucan.Ability]ServiceMethod` — capabilities keyed by ability string
- Default codec is CAR (inbound)
- Default authorization: `validator.IsSelfIssued`

### Pattern: Register a capability handler (Provide)
**When:** Adding a handler for a specific UCAN capability
**Template:**
```go
import "github.com/storacha/go-ucanto/server"

// Handler function signature
func handleBlobAllocate(
    ctx context.Context,
    cap blob.AllocateCaveats,   // typed caveats from capability
    inv invocation.Invocation,
    ictx server.InvocationContext,
) (OkResult, fx.Effects, error) {
    // 1. Business logic
    // 2. Return result + optional effects (fork/join)
    return result, fx.NewEffects(fx.WithFork(...)), nil
}

// Register with Provide (wraps with UCAN validation)
server.WithServiceMethod(
    blob.AllocateAbility,                    // "blob/allocate"
    server.Provide(blob.Allocate, handleBlobAllocate),
)
```
**Key files:** `go-ucanto/server/handler.go`
**Gotchas:**
- `Provide()` automatically validates the UCAN invocation before calling the handler
- Handler receives typed caveats (not raw IPLD), thanks to the capability parser
- Return `(result, effects, error)` — effects for fork/join chains

### Pattern: Define a capability (go-libstoracha)
**When:** Creating a new UCAN capability definition in Go
**Template:**
```go
import (
    "github.com/storacha/go-ucanto/ucan"
    "github.com/storacha/go-ucanto/validator"
    "github.com/storacha/go-ucanto/validator/schema"
)

// 1. Define the ability string
const AllocateAbility = "blob/allocate"

// 2. Define caveats struct
type AllocateCaveats struct {
    Space did.DID
    Blob  types.Blob
    Cause ucan.Link
}

// 3. Implement ToIPLD for serialization
func (ac AllocateCaveats) ToIPLD() (datamodel.Node, error) {
    return ipld.WrapWithRecovery(&ac, AllocateCaveatsType(), types.Converters...)
}

// 4. Create caveats reader (deserializer) from IPLD schema
var AllocateCaveatsReader = schema.Struct[AllocateCaveats](AllocateCaveatsType(), nil, types.Converters...)

// 5. Create the capability
var Allocate = validator.NewCapability(
    AllocateAbility,
    schema.DIDString(),          // resource schema
    AllocateCaveatsReader,       // caveats reader
    validator.DefaultDerives,    // derivation rules
)
```
**Key files:** `go-libstoracha/capabilities/blob/allocate.go`
**Available capability packages:**
```
access, account, assert, blob, claim, consumer, filecoin, http,
pdp, provider, space, types, ucan, upload, web3.storage
```

### Pattern: go-cid usage (CID creation and parsing)
**When:** Working with content identifiers in Go
**Template:**
```go
import (
    "github.com/ipfs/go-cid"
    "github.com/multiformats/go-multihash"
    "github.com/multiformats/go-multicodec"
)

// Create a CIDv1
hash, err := multihash.Sum(data, multihash.SHA2_256, -1)
c := cid.NewCidV1(uint64(multicodec.DagCbor), hash)

// Parse from string
c, err := cid.Decode("bafy...")

// Parse from bytes
c, err := cid.Cast(cidBytes)

// Access components
c.Version()    // 0 or 1
c.Type()       // codec (uint64)
c.Hash()       // multihash bytes
c.String()     // string representation
c.Equals(other)
```
**Key files:** `go-cid` (external dependency)

### Pattern: go-ipld-prime node construction
**When:** Building IPLD data structures in Go
**Template:**
```go
import (
    "github.com/ipld/go-ipld-prime"
    "github.com/ipld/go-ipld-prime/node/basicnode"
    "github.com/ipld/go-ipld-prime/node/bindnode"
)

// Basic node (untyped)
builder := basicnode.Prototype.Map.NewBuilder()
ma, _ := builder.BeginMap(2)
ma.AssembleKey().AssignString("name")
ma.AssembleValue().AssignString("Alice")
ma.AssembleKey().AssignString("age")
ma.AssembleValue().AssignInt(30)
ma.Finish()
node := builder.Build()

// Bind node (struct ↔ IPLD via reflection)
type Person struct {
    Name string
    Age  int64
}
p := &Person{Name: "Alice", Age: 30}
node := bindnode.Wrap(p, personSchema)

// Read from node
name, _ := node.LookupByString("name")
nameStr, _ := name.AsString()
```
**Key files:** `go-ipld-prime/node/basicnode/`, `go-ipld-prime/node/bindnode/`
**Three implementation strategies:**
1. **basicnode**: General-purpose, unstructured (Go maps/slices). Good default.
2. **bindnode**: Maps to/from native Go structs via reflection. Used heavily in go-libstoracha.
3. **codegen**: Generates Go code from IPLD schemas. Maximum performance.

### Pattern: Service entry points
**When:** Understanding how Go services are structured
**Template (urfave/cli — indexing-service):**
```go
app := &cli.App{
    Name:  "indexing-service",
    Commands: []*cli.Command{serverCmd, awsCmd, queryCmd},
}
app.Run(os.Args)
```
**Template (cobra/viper — Piri):**
```go
var rootCmd = &cobra.Command{Use: "piri"}
rootCmd.AddCommand(serve.Cmd, wallet.Cmd, identity.Cmd, delegate.Cmd, client.Cmd, status.Cmd)
```
**Template (Lambda — Piri blob operations):**
```go
func main() {
    lambda.StartHTTPHandler(makeHandler)
}
func makeHandler(cfg aws.Config) (http.Handler, error) {
    service, _ := aws.Construct(cfg)
    handler := blobs.NewBlobPutHandler(service.Blobs().Presigner(), ...)
    return telemetry.NewErrorReportingHandler(handler), nil
}
```
**Key files:** `indexing-service/cmd/main.go`, `piri/cmd/cli/root.go`, `piri/cmd/lambda/putblob/main.go`

## JS ↔ Go Mapping

| Concept | JS (ucanto) | Go (go-ucanto) |
|---------|-------------|----------------|
| Define capability | `capability({ can, with, nb })` | `validator.NewCapability(can, schema, reader, derives)` |
| Handle capability | `Server.provide(cap, handler)` | `server.Provide(cap, handler)` |
| Create server | `Server.create({ service, ... })` | `server.NewServer(signer, opts...)` |
| Register handler | Service object nesting | `server.WithServiceMethod(can, handler)` |
| Caveat types | TypeScript generics + Schema | IPLD schema strings + Go generics |
| Receipt types | Dynamic | `ReceiptReader[Ok, Err]` with IPLD schema |
| Effects | `Server.ok({}).fork(fx)` | `fx.NewEffects(fx.WithFork(...))` |
| Transport | `CAR.inbound` | `car.NewInboundCodec()` |
| Signer | `ed25519.Signer.generate()` | `ed25519.Parse(key)` |

## Key Files Index

| Role | File |
|------|------|
| go-ucanto server | `go-ucanto/server/server.go` |
| go-ucanto Provide | `go-ucanto/server/handler.go` |
| go-ucanto client | `go-ucanto/client/client.go` |
| go-ucanto ed25519 | `go-ucanto/principal/ed25519/` |
| go-ucanto validator | `go-ucanto/core/validator/` |
| go-libstoracha blob caps | `go-libstoracha/capabilities/blob/` |
| go-libstoracha assert caps | `go-libstoracha/capabilities/assert/` |
| go-libstoracha pdp caps | `go-libstoracha/capabilities/pdp/` |
| go-libstoracha IPNI publisher | `go-libstoracha/ipnipublisher/` |
| Indexing service entry | `indexing-service/cmd/main.go` |
| Indexing service server | `indexing-service/cmd/server.go` |
| Piri CLI entry | `piri/cmd/cli/root.go` |
| Piri Lambda handlers | `piri/cmd/lambda/` |

## Go Service Catalog

| Service | CLI Framework | HTTP Framework | DI | Key Feature |
|---------|--------------|----------------|-----|-------------|
| piri | Cobra/Viper | go-ucanto HTTP | uber/fx | Storage node, PDP proofs |
| indexing-service | urfave/cli | Echo + go-ucanto | manual | Content routing, IPNI |
| etracker | Cobra | go-ucanto HTTP | - | Egress tracking |
| delegator | Cobra/Viper | Echo | uber/fx | Provider registration |
| piri-signing-service | Cobra/Viper | Echo + go-ucanto | - | EIP-712 signing |
| forgectl | Cobra/Viper | - (CLI only) | - | Contract admin |
| storoku | urfave/cli v3 | - (CLI only) | - | Infra code generator |

### Shared Dependencies Across Go Services

| Dependency | Used By | Purpose |
|-----------|---------|---------|
| go-ucanto | piri, indexing-service, etracker, delegator, piri-signing-service | UCAN RPC |
| go-libstoracha | piri, indexing-service, delegator, piri-signing-service | Capabilities |
| filecoin-services/go | piri, piri-signing-service, forgectl | Smart contracts, EIP-712 |
| go-ethereum | delegator, piri-signing-service, forgectl | Ethereum interaction |
| uber/fx | piri, delegator | Dependency injection |
| Echo | indexing-service, delegator, piri-signing-service | HTTP server |

## Go Service Infrastructure Details

### Indexing Service Infrastructure

The indexing service runs as a Docker container on ECS and handles content routing queries. Its infrastructure is relatively lightweight compared to Piri.

**Runtime Dependencies:**
- **Redis** (`go-redis/v9`) -- caches content routing lookups (multihash -> claims). Critical for performance since IPNI queries and claim resolution are the hot path.
- **AWS SDK v1 + v2** -- reads from legacy content-claims DynamoDB table and S3 bucket. The dual SDK versions exist because the legacy infra was built with SDK v1.
- **IPFS Datastore** -- local state storage (go-datastore abstraction).

**External Data Sources (not owned, read-only access):**
- Legacy content-claims DynamoDB table (from `content-claims` repo's SST stack)
- Legacy content-claims S3 bucket (CAR-encoded claims)
- IPNI nodes (HTTP API queries for provider records)

**Terraform Resources** (in `deploy/app/legacyclaims.tf`):
- IAM policy `task_legacy_dynamodb_query` -- grants DynamoDB `Query` and `GetItem` on legacy claims table
- IAM policy `task_legacy_s3_get` -- grants S3 `GetObject` on legacy claims bucket

**HTTP API Routes** (Echo framework, `pkg/server/server.go`):

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| GET | `/` | GetRootHandler | Service info / health check |
| GET | `/claim/{claim}` | GetClaimHandler | Fetch a specific claim by CID |
| POST | `/claims` | PostClaimsHandler | Submit new claims |
| GET | `/claims` | GetClaimsHandler | Query claims by multihash |
| GET | `/cid/{cid}` | GetIPNICIDHandler | IPNI CID lookup |
| POST | `/ad` | PostAdHandler | Submit IPNI advertisement |
| GET | `/.well-known/did.json` | - | DID document for service identity |

The indexing service also runs a go-ucanto server (registered in `pkg/service/contentclaims/ucanserver.go` and `pkg/construct/construct.go`) for handling UCAN-based claim operations alongside the HTTP REST API.

### Piri Infrastructure Summary

Piri is the most infrastructure-heavy Go service. See `memory/architecture/infrastructure-decisions.md` for the full breakdown. Key highlights:

- **5 DynamoDB tables** (metadata, chunk_links, ran_link_index, allocation_store, acceptance_store)
- **5 S3 buckets** (ipni_store, blob_store, receipt_store, claim_store, ipni_publisher)
- **2 SQS queue pairs** (ipni_publisher, ipni_advertisement_publishing, each with DLQ)
- **32 SQL tables** across job queue (7), PDP scheduler (15), parking (2), PDP operations (5), Ethereum messages (3)
- **Dual deployment**: EC2 full-node (Terraform) + Lambda functions (blob operations)
- **Drivers**: PostgreSQL (GORM + pgx), SQLite (GORM + go-sqlite3), AWS SDK v1+v2, IPFS Datastore

### Guppy Infrastructure Summary

Guppy is a CLI tool (not deployed) with a local SQLite database:

- **15 SQL tables** tracking the data preparation pipeline: sources, spaces, fs_entries, nodes, links, uploads, shards, dag_scans, indexes, etc.
- **Drivers**: BadgerDB, PostgreSQL (pgx, lib/pq), IPFS Datastore
- No cloud infrastructure (runs locally)

### Storoku Infrastructure Summary

Storoku is an infrastructure-as-code generator that defines the full stack for deploying a Go storage service:

- **ECS Fargate** with CodeDeploy blue/green deployment
- **RDS PostgreSQL** with RDS Proxy and bastion host
- **ElastiCache Redis** with IAM auth and cluster mode
- **DynamoDB**, **S3**, **SQS** (with DLQ), **SNS**
- **Full VPC** with public/private/DB/ElastiCache subnets and VPC endpoints
- See `memory/architecture/infrastructure-decisions.md` for full details.

## Design Rationale

- **go-ucanto mirrors ucanto**: Same conceptual model (capabilities, invocations, receipts, effects) adapted to Go idioms. The mapping is intentionally close to reduce cognitive overhead when working across both codebases.
- **IPLD schema strings over codegen**: go-libstoracha uses `bindnode` with IPLD schema strings rather than codegen — balances type safety with development speed. Caveats structs implement `ToIPLD()` for serialization.
- **Multiple CLI frameworks**: indexing-service uses urfave/cli, most services use Cobra/Viper, storoku uses urfave/cli v3. All are standard Go patterns.
- **Lambda + HTTP dual deployment**: Piri supports both AWS Lambda handlers and standalone HTTP servers — the same service layer is shared, only the entry point differs.
- **No DHT**: Content routing uses IPNI (HTTP-based) not Kademlia DHT. This is a deliberate choice for Storacha's architecture — IPNI provides structured, indexed lookups rather than DHT gossip.
- **Ethereum integration**: Three Go services (piri-signing-service, delegator, forgectl) interact with Ethereum for PDP proofs, payment channels, and provider registration.

## Authoritative Specs
- [go-ucanto Source](https://github.com/storacha/go-ucanto)
- [go-libstoracha Source](https://github.com/storacha/go-libstoracha)
- [Piri Source](https://github.com/storacha/piri)
- [Indexing Service Source](https://github.com/storacha/indexing-service)
