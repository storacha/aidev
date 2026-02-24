# w3up

Legacy monorepo for Storacha upload/storage service. `@web3-storage/*` namespace. For active development, prefer `upload-service` repo (`@storacha/*` namespace).

## Quick Reference

```bash
pnpm install
pnpm test              # Run tests across all packages
pnpm build             # Build all packages
```

## Structure

10 packages in `packages/`. Same packages as upload-service but under `@web3-storage/*`:

| Package | Equivalent in upload-service |
|---|---|
| `capabilities` (`@web3-storage/capabilities`) | `@storacha/capabilities` |
| `upload-api` (`@web3-storage/upload-api`) | `@storacha/upload-api` |
| `upload-client` | `@storacha/upload-client` |
| `w3up-client` | `@storacha/client` |
| `access-client` (`@web3-storage/access`) | `@storacha/access` |
| `filecoin-api` | `@storacha/filecoin-api` |
| `filecoin-client` | `@storacha/filecoin-client` |
| `blob-index` | `@storacha/blob-index` |
| `did-mailto` | `@storacha/did-mailto` |
| `eslint-config-w3up` | `@storacha/eslint-config` |

## Key Patterns

Same as upload-service. See upload-service/CLAUDE.md for details.

- **Versioning**: Release Please with Conventional Commits (see CONTRIBUTING.md)
- External repos that haven't migrated still import from this namespace

## When to Use This Repo

- When working on repos that still depend on `@web3-storage/*` packages
- For reference when debugging version mismatches between `@web3-storage/*` and `@storacha/*`
