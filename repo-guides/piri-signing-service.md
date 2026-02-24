# piri-signing-service

Go service that wraps a cold wallet to provide EIP-712 signatures for PDP (Proof of Data Possession) operations on Filecoin. Piri nodes request signatures here without exposing Storacha's private key.

## Quick Reference

```bash
make build              # go build -o signing-service .
make test               # go test -v ./...
make lint               # golangci-lint
./signing-service       # Start server (reads signer.yaml or SIGNING_SERVICE_* env)
```

## Structure

```
main.go                 # Entry point (Cobra CLI)
pkg/
  config/               # Config loading (CLI > env > file), private key loading
  signer/               # EIP-712 signer (CreateDataSet, AddPieces, SchedulePieceRemovals, DeleteDataSet)
  handlers/             # HTTP endpoint handlers (legacy /sign/* routes)
  server/               # UCAN server setup with access/grant capability
    handlers/           # UCAN invocation handlers
  inprocess/            # In-process signer for UCAN invocations
  types/                # Request/response types
  client/               # Go client library
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/healthcheck` | Service health (shows signer address, chain ID) |
| POST | `/` | UCAN invocation endpoint (primary) |
| POST | `/sign/create-dataset` | Legacy: Sign CreateDataSet |
| POST | `/sign/add-pieces` | Legacy: Sign AddPieces |
| POST | `/sign/schedule-piece-removals` | Legacy: Sign SchedulePieceRemovals |
| POST | `/sign/delete-dataset` | Legacy: Sign DeleteDataSet |

## UCAN Capabilities

| Capability | Handler | Purpose |
|---|---|---|
| `access/grant` | `pkg/server/handlers/` | Grant delegations for signing operations |

Extracts capabilities from access grant requests, issues time-limited delegations (1 hour validity).

## Key Dependencies

- `github.com/ethereum/go-ethereum` — ECDSA signing, keystore, RPC
- `github.com/storacha/go-ucanto` — UCAN protocol
- `github.com/storacha/filecoin-services/go` — EIP-712 signing utilities
- `github.com/labstack/echo/v4` — HTTP server

## What Breaks If You Change Things Here

- Signing format changes break PDP proof verification on-chain
- Key management changes affect all piri nodes' ability to produce valid proofs
- Legacy /sign/* endpoints may still be in use — don't remove without checking
