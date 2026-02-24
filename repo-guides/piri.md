# piri

Go storage node. Handles blob storage, PDP proofs (Ethereum), retrieval, replication, and egress tracking.

## Quick Reference

```bash
make build              # go build -o ./piri ./cmd
make test               # go test ./...
./piri serve            # Start all services (urfave/cli → cobra/viper)
```

## Structure

```
cmd/
  main.go               # Entry point
  cli/serve/            # Serve subcommands (ucan, retrieval, etc.)
pkg/
  service/
    storage/            # Blob storage UCAN service
      ucan.go           # UCAN server setup (5 capability handlers)
      handlers/         # Individual UCAN handlers
        blob/accept.go  # blob/accept → CommP calculation, PDP, location claim
        blob/allocate.go
        replica/        # Replication handlers
    retrieval/          # space/content/retrieve handler
    egresstracker/      # Egress tracking service
    publisher/          # IPNI advertisement publishing
  fx/                   # uber/fx dependency injection modules
    pdp/                # PDP proof system
    blobs/              # Blob storage
    claims/             # Claims server
    retrieval/          # Retrieval service
    replicator/         # Replication queue
    scheduler/          # Task engine for PDP challenges
  pdp/
    aggregation/
      commp/commp.go    # FR32 padding + CommP calculation
      aggregator/       # Piece aggregation into proof sets
```

## UCAN Capabilities Handled

| Capability | Handler |
|---|---|
| `blob/allocate` | `pkg/service/storage/ucan/blob_allocate.go` |
| `blob/accept` | `pkg/service/storage/ucan/blob_accept.go` |
| `pdp/info` | `pkg/service/storage/ucan/pdp_info.go` |
| `access/grant` | `pkg/service/storage/ucan/access_grant.go` |
| `blob/replica/allocate` | `pkg/service/storage/ucan/replica_allocate.go` |
| `space/content/retrieve` | `pkg/fx/retrieval/ucan/handlers/` |

## Key Patterns

- **Dependency injection**: uber/fx (`pkg/fx/` modules)
- **Job queues**: SQLite-backed job queues for async processing (CommP calc, replication, aggregation)
- **PDP proofs**: Ethereum smart contract integration for proof-of-data-possession
- **Logging**: `go-log/v2` with `log.Infow()`, `log.Warnw()`
- **Config**: cobra/viper CLI, environment variables

## What Breaks If You Change Things Here

- `blob/accept` triggers the entire PDP pipeline — changes cascade through CommP, aggregation, Ethereum
- Retrieval handler changes affect client content access
- `go-ucanto` or `go-libstoracha` updates require capability definition alignment with JS
