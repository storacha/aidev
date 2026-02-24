# w3infra

AWS infrastructure for Storacha services. Deploys upload-api handlers, Filecoin pipeline, and supporting infra via SST (Serverless Stack).

## Quick Reference

```bash
pnpm install
pnpm test              # Run tests
npx sst build          # SST build
npx sst deploy         # Deploy to AWS
```

## Structure

```
billing/               # Stripe billing integration, usage aggregation
carpark/               # R2/S3 CAR storage infrastructure
filecoin/              # Filecoin pipeline infrastructure
indexer/               # Indexing service integration
lib/                   # Shared utilities
upload-api/            # Lambda handlers wrapping @storacha/upload-api
  external-services/   # External service configurations
    ipni-service.js    # IPNI service wrapper
    sso-providers/     # SSO provider configuration
stacks/                # SST stack definitions
```

## Key Patterns

- **SST stacks**: Define DynamoDB tables, S3 buckets, Lambda functions, API Gateway
- **Lambda handlers**: Thin wrappers that instantiate `@storacha/upload-api` with AWS-specific storage backends
- **External services**: Configures connections to IPNI, content-claims, Stripe
- **Environment**: DynamoDB for allocations/provisions/delegations, R2/S3 for blob storage

## What Breaks If You Change Things Here

- Stack changes affect all deployed services
- DynamoDB table schema changes require careful migration
- Environment variable changes need coordinated deployment
- `@storacha/upload-api` version bumps may require handler adjustments
