# delegator

Go service for storage provider registration and delegation management. Validates provider identities, manages registration in DynamoDB, issues UCAN delegations, and benchmarks provider performance.

## Quick Reference

```bash
make build              # go build -o bin/delegator ./main.go
make test               # go test -v ./...
./bin/delegator serve --host 0.0.0.0 --port 8080
```

## Structure

```
cmd/                    # CLI commands (Cobra)
internal/
  config/               # Viper configuration (flags/env/files)
  handlers/             # HTTP endpoint handlers
  server/               # Echo HTTP server + routing
  services/
    registrar/          # Core delegation logic, UCAN proof validation
    benchmark/          # Upload/download performance testing
      client/           # Invokes blob/allocate, blob/accept on storage nodes
  providers/            # Dependency providers (signer, DIDs, proofs)
  store/                # DynamoDB persistence (provider registry, allowlist)
client/                 # Go client library for external consumption
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/healthcheck` | Service health |
| GET | `/.well-known/did.json` | DID document |
| PUT | `/registrar/register-node` | Register storage provider |
| GET | `/registrar/is-registered` | Check provider registration |
| GET | `/registrar/request-proofs` | Request delegation proofs |
| POST | `/benchmark/upload` | Benchmark upload performance |
| POST | `/benchmark/download` | Benchmark download performance |

## UCAN Capabilities

- **Validates** in operator proofs: `blob/accept`, `blob/allocate`, `blob/replica/allocate`, `pdp/info`
- **Issues delegations** for: `claim/cache` (to indexing service), `space/egress` (to egress tracking)

## Key Dependencies

- `go.uber.org/fx` — Dependency injection
- `github.com/labstack/echo/v4` — HTTP server
- `github.com/spf13/cobra` + `viper` — CLI and config
- `github.com/storacha/go-ucanto` — UCAN protocol
- `github.com/storacha/go-libstoracha` — Storacha capabilities
- `github.com/aws/aws-sdk-go-v2` — DynamoDB

## What Breaks If You Change Things Here

- Delegation format changes affect all downstream services (piri, indexing-service, etracker)
- Registration endpoint changes affect storage node onboarding
- Proof validation changes can lock out registered providers
