# filecoin-services

Smart contracts and Go bindings for Storacha's on-chain programmable storage service. Implements FilecoinWarmStorageService (PDP verification + payment rails), ServiceProviderRegistry, and auto-generated Go bindings.

## Quick Reference

```bash
# Top-level
make contracts          # Build all Solidity contracts
make bindings           # Generate Go bindings (depends on contracts)
make test               # Run all tests (contracts + go)

# Solidity (service_contracts/)
make build              # forge build --via-ir
make test               # forge test --via-ir -vv
make gen                # Regenerate layout, internal lib, view contract
make update-abi         # Extract ABIs to abi/

# Go (go/)
make generate           # Auto-generate bindings + error types from ABIs
make test               # go test ./...

# Subgraph (subgraph/)
pnpm codegen && pnpm build
```

## Structure

```
service_contracts/
  src/
    FilecoinWarmStorageService.sol    # Core: PDP + payments (1,657 LoC, UUPS upgradeable)
    ServiceProviderRegistry.sol       # Provider registry (769 LoC, UUPS upgradeable)
    FilecoinWarmStorageServiceStateView.sol  # Read-only view via extsload
    Errors.sol                        # 50+ custom error types
    lib/
      SignatureVerificationLib.sol    # EIP-712 sig verification (deployed separately)
      FilecoinWarmStorageServiceStateLibrary.sol  # Auto-generated state reads
  test/                               # Foundry tests
  tools/                              # Deploy scripts (calibnet, mainnet)
  abi/                                # Extracted JSON ABIs
  lib/                                # Git submodules (forge-std, openzeppelin, pdp, fws-payments)
go/
  bindings/                           # Auto-generated contract bindings (abigen)
    filecoin_warm_storage_service.go  # Main service binding (236KB)
    service_provider_registry.go      # Registry binding
    payments.go                       # FilecoinPayV1 binding
    pdp_verifier.go                   # PDP verifier binding
  eip712/                             # EIP-712 type definitions + signing
    types.go                          # CreateDataSet, AddPieces, SchedulePieceRemovals, DeleteDataSet
    signature.go                      # Signature generation/verification
  evmerrors/                          # Auto-generated EVM error decoding
    errors.go                         # Typed Go errors from contract ABIs
    cmd/error-binding-generator/      # Code generator tool
subgraph/                             # The Graph indexing (AssemblyScript)
  src/                                # Event handler mappings
  schemas/                            # GraphQL schemas
  config/                             # Network configs (calibration, mainnet)
```

## Smart Contracts

| Contract | Purpose |
|----------|---------|
| FilecoinWarmStorageService | Core service: dataset management, PDP challenge/prove, payment validation, fault handling |
| ServiceProviderRegistry | Provider registration, products, pricing, capabilities |
| SignatureVerificationLib | EIP-712 signature verification (external library to stay under 24KiB) |
| StateView + StateLibrary | Efficient storage reads via `extsload` pattern |

**Key patterns:**
- UUPS Upgradeable (OpenZeppelin) — never reorder storage fields
- EIP-712 signatures for off-chain authorization (CreateDataSet, AddPieces, etc.)
- PDPListener interface — receives challenge/prove callbacks
- 24KiB code size limit managed via external libraries + extsload

## Go Package

Module: `github.com/storacha/filecoin-services/go`

Used by: piri, piri-signing-service, forgectl, delegator

**eip712/types.go** defines the signing types that must match Solidity exactly:
- `CreateDataSet`, `AddPieces`, `SchedulePieceRemovals`, `DeleteDataSet`

## Code Generation Chain

```
foundry.toml (remappings) → Solidity compilation
  → make gen (auto-generate StateLibrary, StateView, Layout)
  → make update-abi (extract ABIs)
  → go/make generate (abigen → Go bindings, error-binding-generator → error types)
  → subgraph/pnpm codegen (GraphQL types from schema)
```

**After ANY contract change:** run `make gen` in service_contracts/, `make generate` in go/, rebuild subgraph.

## What Breaks If You Change Things Here

- **Storage layout changes** → Must regenerate StateLibrary, StateView, Layout. Go bindings stale. Subgraph queries fail.
- **Method signature changes** → Go bindings break. Subgraph event handlers may not match.
- **Error definition changes** → Go evmerrors package must be regenerated.
- **EIP-712 type changes** → Go eip712/types.go must match exactly or signatures fail.
- **Dependency submodule updates** → May change PDP/payment interfaces. Test all integration points.
- **Adding large logic** → May exceed 24KiB limit. Use external libraries + extsload pattern.
- **Storage field reordering** → Breaks UUPS proxy upgrades. Only append new fields at end.
