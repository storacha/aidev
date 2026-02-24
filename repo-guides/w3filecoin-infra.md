# w3filecoin-infra

AWS infrastructure for the Filecoin pipeline. Deploys aggregator, dealer, and deal-tracker services via SST.

## Quick Reference

```bash
npm install
npm test -w packages/core   # Test core package
npx sst build               # SST build
```

## Structure

```
packages/
  core/              # Shared types and utilities
  infra/             # SST stacks (DynamoDB, Lambda, SQS)
```

## Filecoin Pipeline Services Deployed

- **Aggregator**: Processes `piece/offer`, collects pieces into aggregates
- **Dealer**: Processes `aggregate/offer`, arranges Filecoin deals
- **Deal-tracker**: Tracks deal status on Filecoin chain

## Key Dependencies

- `@storacha/filecoin-api` — Service implementations
- `@storacha/capabilities` — Capability definitions
- `@storacha/filecoin-client` — Client invocations

## What Breaks If You Change Things Here

- Pipeline infrastructure changes affect data durability guarantees
- Queue configuration changes affect processing throughput
- DynamoDB schema changes require migration
