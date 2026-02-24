# forgectl

Go CLI tool for administering Storacha Forge network smart contracts. Manages payment channels, provider registration, and collects metrics (payment status, fault tracking) for OTLP monitoring.

## Quick Reference

```bash
make build              # go build -o forgectl .
make test               # go test ./...
make install            # go install
./forgectl providers list
./forgectl payments status
./forgectl metrics payments
```

## Structure

```
main.go                 # Entry point (Cobra)
cli/
  cmd/
    root.go             # Root command with 3 subcommands
    providers/
      list.go, get.go, approve.go       # Provider management
    payments/
      deposit.go, status.go,            # Payment channel ops
      approveoperator.go, revokeoperator.go,
      authorizesession.go, calculate.go, settlerail.go
    metrics/
      payments.go       # Collect payment metrics via OTLP
      faults.go         # Collect fault metrics via OTLP
  config/               # Config loading (config.yaml or env)
  printer/              # TUI output (charmbracelet/bubbletea)
```

## Commands

| Command | Purpose |
|---------|---------|
| `providers list` | List registered storage providers |
| `providers get` | Get provider details |
| `providers approve` | Approve a provider |
| `payments deposit` | Deposit funds to payment channel |
| `payments status` | View payment status |
| `payments approveoperator` | Approve payment operator |
| `payments revokeoperator` | Revoke payment operator |
| `payments authorizesession` | Create session key |
| `payments calculate` | Calculate payment amounts |
| `payments settlerail` | Settle payment rail |
| `metrics payments` | Export payment metrics (OTLP) |
| `metrics faults` | Export fault metrics (OTLP) |

## Key Dependencies

- `github.com/ethereum/go-ethereum` — Blockchain interaction
- `github.com/storacha/filecoin-services/go` — Smart contract bindings
- `github.com/charmbracelet/bubbletea` — Terminal UI
- `go.opentelemetry.io/otel` — OTLP metrics export
- `github.com/spf13/cobra` + `viper` — CLI and config

## Configuration

Requires contract addresses in `config.yaml` or `FORGECTL_*` env vars:
- FilecoinWarmStorageService, PDPVerifier, ServiceProviderRegistry
- Payments, USDFC token, SessionKeyRegistry
- Supports Ethereum keystore authentication

## What Breaks If You Change Things Here

- Self-contained admin tool — no blast radius to other services
- Contract interaction changes must match deployed contract ABIs
- Metrics format changes affect monitoring dashboards
