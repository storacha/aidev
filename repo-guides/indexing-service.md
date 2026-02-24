# indexing-service

Go service for content routing. Bridges IPNI (InterPlanetary Network Indexer) with content claims.

## Quick Reference

```bash
make build              # go build -o ./indexer ./cmd
make test               # go test -race -v ./...
go run ./cmd server     # Start server
go run ./cmd aws        # Start AWS Lambda handler
```

## Structure

```
cmd/
  main.go               # Entry point (server or aws subcommands)
  server.go             # HTTP server setup
  aws.go                # Lambda handler
pkg/
  server/server.go      # HTTP mux with all routes
  service/
    contentclaims/
      ucanserver.go     # UCAN server for assert/equals, assert/index, claim/cache
      ucanservice.go    # Handler implementations
  construct/construct.go # Dependency injection / service construction
  types/types.go        # Core interfaces
```

## HTTP Routes

| Route | Handler | Purpose |
|---|---|---|
| `GET /` | GetRootHandler | Service info |
| `GET /claim/{claim}` | GetClaimHandler | Fetch single claim by CID |
| `POST /` and `POST /claims` | PostClaimsHandler | UCAN invocations (assert/*, claim/cache) |
| `GET /claims` | GetClaimsHandler | Query claims by multihash |
| `GET /.well-known/did.json` | GetDIDDocument | DID document |
| `GET /cid/{cid}` | GetIPNICIDHandler | IPNI lookup by CID |

## UCAN Capabilities Handled

- `assert/equals` — Store equals claim (from filecoin/submit)
- `assert/index` — Store index claim (from index/add)
- `claim/cache` — Cache claims from storage nodes

## Key Patterns

- Uses `go-ucanto` for UCAN server (`server.NewServer()` with `server.WithServiceMethod()`)
- Uses `go-libstoracha` for capability definitions
- IPNI integration via `go-libipni` (advertisement publishing, content routing)
- Telemetry via OpenTelemetry

## What Breaks If You Change Things Here

- Claim format/schema changes affect content routing for the entire network
- IPNI advertisement changes affect content discoverability
- `go-libstoracha` capability changes must match JS `@storacha/capabilities`
