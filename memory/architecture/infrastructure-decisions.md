<!-- Last validated: 2026-02-20 | Source: repo analysis -->
# Infrastructure Decisions & Patterns

> **TL;DR:** Storacha runs on Cloudflare (Workers for Freeway/KMS/w3clock, R2 for CAR storage, KV for auth caches, Queues for egress) + AWS (Lambda for Upload API, DynamoDB for ~25 tables, SQS for pipeline queues, S3 for delegations/workflow). SST (Serverless Stack) manages AWS infra-as-code across w3infra, content-claims, and w3filecoin-infra. Key rationale: R2 for zero-egress from Workers, DynamoDB for serverless scale, FIFO queues for Filecoin exactly-once processing.

> Why these infrastructure choices, how they're configured, and the key schemas.

## Deployment Model Overview

```
                    Storacha Infrastructure

  Cloudflare                          AWS (us-west-2)
  ─────────                           ───────────────
  Workers:                            Lambda + API Gateway:
    Freeway (gateway)                   Upload API (ucan-invocation-router)
    UCAN KMS                            Billing handlers
    w3clock                             Metrics aggregators
    Hoverboard                          Receipt handler

  R2 Buckets:                         S3 Buckets:
    carpark-{stage}-0                   delegation-store
                                        workflow-store
  KV Namespaces:                        stream-log-store
    AUTH_TOKEN_METADATA                 aggregator-buffer-store
    CONTENT_SERVE_DELEGATIONS_STORE     dealer-offer-store
    DAGPB_CONTENT_CACHE
                                      DynamoDB: ~25+ tables
  Queues:                             SQS: 8+ queues
    egress-tracking-queue             EventBridge: carpark.internal events
                                      Kinesis: UCAN invocation logging
  Service Bindings:
    reads → edge-gateway → API
```

## SST (Serverless Stack) Patterns

Three repos use SST for AWS infrastructure-as-code:

| Repo | Region | Runtime | Stacks |
|------|--------|---------|--------|
| w3infra | us-west-2 | nodejs20.x arm_64 | 13 stacks |
| content-claims | us-west-2 | nodejs20.x | 3 stacks (Bucket, DB, API) |
| w3filecoin-infra | us-west-2 | nodejs20.x arm_64 | 5 stacks |

### SST Stack Organization Pattern

```js
// sst.config.ts — multi-stack orchestration
stacks(app) {
  app.stack(DbStack)         // DynamoDB tables first
  app.stack(BucketStack)     // S3 buckets
  app.stack(QueueStack)      // SQS queues
  app.stack(ApiStack)        // Lambda + API Gateway (references above)
  app.stack(EventStack)      // EventBridge rules
}
```

**Pattern:** Stacks reference each other via `use()`:
```js
function ApiStack({ stack, app }) {
  const { table } = use(DbStack)
  const { bucket } = use(BucketStack)
  // ...
}
```

### Environment Isolation

- **Bucket naming:** `{name}-{stage}-{version}` (e.g., `carpark-prod-0`)
- **Config helpers:** `isProd`, `isStaging`, `isPrBuild` booleans
- **PR builds:** Use `DESTROY` removal policy for automatic cleanup
- **Stage parameter:** Flows through all resource names

## DynamoDB Schema Catalog

### w3infra — Upload API Tables

| Table | PK | SK | GSIs | Stream | Purpose |
|-------|----|----|------|--------|---------|
| allocation | space (DID) | multihash | multihash; insertedAt | - | Track allocated blobs per space |
| blob-registry | space | digest | digest | - | Blob registration info |
| store | space | link (CAR CID) | cid | - | Stored CAR files mapping |
| upload | space | root | cid | - | CAR shards → upload root CID |
| delegation | link (CID) | - | audience; issuer+audience | - | Delegation index |
| revocation | revoke (CID) | - | - | - | Revocation tracking |
| subscription | subscription | provider | customer+provider; provider | - | Customer-provider links |
| consumer | subscription | provider | consumer; consumerV2; provider; customer | - | Space-subscription links |
| rate-limit | id | - | subject | - | Rate limit records |
| storage-provider | provider (DID) | - | - | - | Provider registry |
| replica | pk (space#digest) | provider | - | - | Blob replica tracking |
| piece-v2 | piece | - | content; stat+insertedAt | new_image | CAR → piece mapping |

### w3infra — Billing Tables

| Table | PK | SK | GSIs | Stream | Purpose |
|-------|----|----|------|--------|---------|
| customer | customer (DID) | - | account (Stripe ID) | - | Customer accounts |
| usage | customer | sk (from#provider#space) | - | new_image | Per-space usage tracking |
| space-snapshot | - | - | - | - | Usage snapshots |
| space-diff | - | - | - | - | Usage deltas |
| egress-traffic-events | - | - | - | - | Egress records |

### w3filecoin-infra — Filecoin Pipeline Tables

| Table | PK | SK | GSIs | Stream | Purpose |
|-------|----|----|------|--------|---------|
| aggregator-piece-store | piece | group | - | - | Piece buffering (OFFERED/ACCEPTED) |
| aggregator-aggregate-store | aggregate | - | group | new_and_old | Aggregate collection |
| aggregator-inclusion-store | aggregate | piece | indexPiece (piece+group) | new_and_old | Inclusion proofs |
| dealer-aggregate-store | aggregate | - | stat+insertedAt | new_and_old | Deal aggregates (OFFERED/APPROVED/REJECTED) |
| deal-tracker-deal-store-v1 | piece | dealId | piece | new_and_old | Filecoin deal state |

### content-claims — Claims Table

| Table | PK | SK | TTL | Purpose |
|-------|----|----|-----|---------|
| claims-v1 | content (multihash, base58btc) | claim (CID, base32) | expiration | Content claims lookup |

Query pattern: by content multihash → get all claims (limit 100).

## S3/R2 Bucket Catalog

### R2 (Cloudflare)
| Bucket | Used By | Purpose |
|--------|---------|---------|
| carpark-{stage}-0 | Freeway, Upload API | Primary CAR shard storage |

### S3 (AWS)
| Bucket | Used By | Purpose |
|--------|---------|---------|
| delegation-store | w3infra | UCAN delegation archives |
| workflow-store | w3infra | Agent message / invocation storage |
| stream-log-store | w3infra | UCAN stream log (Kinesis → S3) |
| upload-shards-store | w3infra | Large shard lists (>5k shards) |
| claims-v1 | content-claims | CAR-encoded claim storage (public read) |
| aggregator-buffer-store | w3filecoin-infra | Buffered pieces |
| aggregator-inclusion-proof-store | w3filecoin-infra | Inclusion proof data |
| dealer-offer-store | w3filecoin-infra | Deal offers |
| deal-tracker-deal-archive-store | w3filecoin-infra | Deal archives |

**Claim storage key pattern:** `{cidstr}/{cidstr}.car` (base32 encoded)

## Queue Architecture

### SQS (AWS)
| Queue | Type | DLQ | Purpose |
|-------|------|-----|---------|
| filecoin-submit-queue | Standard | - | Filecoin pipeline submissions |
| piece-offer-queue | Standard | - | Piece offers to aggregator |
| block-advert-publisher-queue | Standard | - | IPNI advertisement publishing |
| block-index-writer-queue | Standard | - | Block index writes |
| egress-traffic-queue | Standard | - | Egress event processing |
| piece-queue | Standard | Yes (14d) | 1st Filecoin processor |
| buffer-queue.fifo | FIFO | Yes (14d) | 2nd processor (content-based dedup) |
| aggregate-offer-queue.fifo | FIFO | Yes (14d) | 3rd processor (aggregate offers) |

**Pattern:** Filecoin pipeline uses FIFO queues with content-based deduplication for exactly-once processing.

### Cloudflare Queues
| Queue | Used By | Purpose |
|-------|---------|---------|
| egress-tracking-queue-{stage} | Freeway | Egress event tracking |

### Event Sources
- **EventBridge:** Source `carpark.internal` — fires on CAR blob puts
- **DynamoDB Streams:** `piece-v2`, `usage`, filecoin tables → Lambda consumers
- **Kinesis:** UCAN invocation logging (10 MiB max record)

## Wrangler / Cloudflare Worker Patterns

### Freeway (Primary Gateway Worker)

```toml
# wrangler.toml
[[r2_buckets]]
binding = "CARPARK"
bucket_name = "carpark-prod-0"

[[kv_namespaces]]
binding = "AUTH_TOKEN_METADATA"
binding = "CONTENT_SERVE_DELEGATIONS_STORE"
binding = "DAGPB_CONTENT_CACHE"

[[queues.producers]]
binding = "EGRESS_QUEUE"
queue = "egress-tracking-queue-production"
```

No service bindings — uses direct R2/KV access.

### reads/edge-gateway (Service Binding Example)

```toml
[[env.production.services]]
binding = "API"
service = "nftstorage-link-api-production"

[[env.production.services]]
binding = "CID_VERIFIER"
service = "dotstorage-cid-verifier-production"

[[env.production.services]]
binding = "DENYLIST"
service = "dotstorage-denylist-production"
```

**Pattern:** Service bindings provide Worker-to-Worker direct calls (no HTTP overhead, no cold starts for the target worker).

### Cloudflare D1

**Not used** in core Storacha services. D1 references found only in test files and non-core repos (eliza, linkdex).

### Cloudflare Durable Objects

| Service | DO Class | Purpose |
|---------|----------|---------|
| w3clock | DurableClock | Persistent Merkle clock state per space |
| w3name | - | Name resolution state |

**Pattern:** DOs provide single-writer consistency for CRDT clock heads. Each space gets its own DO instance addressed by space DID.

## Infrastructure Decision Rationale

### Why R2 for CAR storage (not S3)?
- Freeway (gateway) is a Cloudflare Worker — R2 provides zero-egress-cost access from Workers
- CDN integration: R2 + CF Workers = automatic global caching
- Upload API (AWS Lambda) can also write to R2 via S3-compatible API

### Why DynamoDB (not D1 or RDS)?
- Upload API runs on Lambda — DynamoDB is the natural serverless DB
- Single-digit ms latency at scale, automatic scaling
- GSI pattern enables multiple access patterns per table
- DynamoDB Streams feed event-driven pipeline processing

### Why FIFO queues for Filecoin pipeline?
- Exactly-once processing via content-based deduplication
- Piece aggregation is idempotent but duplicate processing wastes compute
- Dead letter queues with 14-day retention for debugging failed pieces

### Why Cloudflare KV for auth metadata?
- Read-heavy, write-infrequent (delegation caches, auth tokens)
- Global edge replication — sub-ms reads from any CF PoP
- Eventually consistent is acceptable for auth token lookups

### Why Durable Objects for clock state?
- Merkle clock needs single-writer semantics (prevent concurrent head updates)
- DO provides exactly this: one instance per key, consistent read-after-write
- Small state footprint (just head CID + recent events)

## Go Service Infrastructure (Terraform-managed)

Unlike the JS services (SST on AWS + Cloudflare Workers), the Go services use **Terraform** for infrastructure-as-code and deploy to AWS as Docker containers (ECS) or Lambda functions. These services have their own DynamoDB tables, S3 buckets, SQS queues, and SQL databases separate from the SST-managed w3infra stack.

### Piri — Storage Node

Piri has the most complex infrastructure of any Go service. It runs as a Docker container on EC2 (full-node deployment) or as Lambda functions (blob operations), and manages PDP (Provable Data Possession) proofs on Ethereum.

**DynamoDB Tables:**

| Table | Purpose |
|-------|---------|
| `metadata` | Node metadata storage |
| `chunk_links` | Links between content chunks |
| `ran_link_index` | Receipt/invocation link index |
| `allocation_store` | Blob allocation records |
| `acceptance_store` | Blob acceptance records |

**S3 Buckets:**

| Bucket | Purpose |
|--------|---------|
| `ipni_store_bucket` | IPNI advertisement storage (with CORS + public read policy) |
| `blob_store_bucket` | Primary blob/CAR storage (with CORS + public read policy) |
| `receipt_store_bucket` | UCAN receipt storage |
| `claim_store_bucket` | Content claim storage |
| `ipni_publisher` | IPNI advertisement publishing (with lifecycle policy for cleanup) |

**SQS Queues:**

| Queue | DLQ | Purpose |
|-------|-----|---------|
| `ipni_publisher` | `ipni_publisher_deadletter` | IPNI advertisement queuing |
| `ipni_advertisement_publishing` | `ipni_advertisement_publishing_deadletter` | IPNI ad publishing pipeline |

Both queues are consumed by Lambda functions (`ipni_publisher_source_mapping`, `ipni_advertisement_publishing_source_mapping`).

**SQL Database (PostgreSQL + SQLite):**

Piri uses a substantial SQL schema for its job queue and PDP scheduler. The job queue supports both SQLite (local dev) and PostgreSQL (production).

*Job Queue Tables (7):* `jobqueue`, `jobqueue_dead`, `queues`, `job_ns`, `jobs`, `job_done`, `job_dead` -- persistent task queue with deduplication and dead-letter support.

*PDP Scheduler Tables (15):* `machines`, `task`, `task_history`, `task_follow`, `task_impl` -- generic task scheduler. `parked_pieces`, `parked_piece_refs` -- piece parking before proof set inclusion. `pdp_services`, `pdp_piece_uploads`, `pdp_piecerefs`, `pdp_proof_sets`, `pdp_prove_tasks`, `pdp_proofset_creates`, `pdp_proofset_roots`, `pdp_proofset_root_adds` -- PDP proof lifecycle management.

*Ethereum Message Tables (3):* `message_sends_eth`, `message_send_eth_locks`, `message_waits_eth` -- track Ethereum transaction sends, locks (to prevent double-sends), and confirmation waits.

**Deployment:** Terraform-managed EC2 instances (full-node) with EBS volumes (`piri_data`, `piri_data_protected`), VPC networking, API Gateway for Lambda endpoints. Also supports a standalone PDP node deployment (`deploy/pdp/`).

**Key Terraform Files:** `deploy/app/dynamodb.tf`, `deploy/app/s3.tf`, `deploy/app/sqs.tf`, `deploy/app/lambda.tf`, `deploy/app/gateway.tf`, `deploy/full-node/`, `deploy/pdp/`, `pkg/pdp/scheduler/schema/task.sql`

### Storoku — Infrastructure Code Generator / Storage Service

Storoku is an infrastructure-as-code generator for storage nodes. Its Terraform modules define the full stack needed to run a storage service on AWS.

**Compute:** ECS Fargate (containerized) with CodeDeploy blue/green deployment, ALB for load balancing.

**DynamoDB:** Generic `table` resource (the actual table name is parameterized per deployment).

**S3 Buckets:** `bucket` (primary storage, with CORS, lifecycle rules, and public access block), `env_file_bucket` (environment configuration files).

**SQS:** `queue` with `queue_deadletter`, plus a `caching` queue for cache invalidation.

**ElastiCache (Redis):** Full Redis cluster with `cache`, `cluster_enabled` replication group, `cache_user_group` with IAM-based auth, `cache_subnet_group`. Used for caching and potentially as a message broker.

**PostgreSQL (RDS):** Full RDS PostgreSQL instance with RDS Proxy for connection pooling, bastion host for debug access, KMS encryption. Database provisioning via a Lambda function (`postgres-provisioner`).

**Networking:** Full VPC with public, private, database, and ElastiCache subnets. VPC endpoints for ECR, CloudWatch, DynamoDB, SQS, SNS, S3 -- minimizes egress and keeps traffic within AWS.

**Key Terraform Files:** `dynamodb/main.tf`, `s3/main.tf`, `sqs/main.tf`, `elasticaches/main.tf`, `postgres/main.tf`, `vpc/main.tf`, `deployment/ecs_task.tf`, `deployment/ecs_service.tf`, `ecs-infra/`

### Indexing Service — Content Routing

The indexing service has minimal self-managed infrastructure. It runs as a Docker container and primarily relies on external data sources (IPNI, content-claims DynamoDB/S3).

**Drivers/Dependencies:**
- **Redis** (`github.com/redis/go-redis`) -- used for caching content routing results
- **AWS SDK v1 + v2** -- for accessing legacy content-claims DynamoDB tables and S3 buckets
- **IPFS Datastore** (`go-datastore`) -- for local state storage

**IAM Permissions (Terraform):**
- `task_legacy_dynamodb_query` -- read access to legacy content-claims DynamoDB table
- `task_legacy_s3_get` -- read access to legacy content-claims S3 bucket

The indexing service does not own its own DynamoDB tables or S3 buckets. Instead, it reads from content-claims infrastructure (cross-service access) and queries IPNI nodes over HTTP.

**Key Terraform Files:** `deploy/app/legacyclaims.tf`

### Guppy — Data Preparation CLI

Guppy is a CLI tool (not a deployed service) that runs locally for data preparation. It uses a local SQLite database (with PostgreSQL support for scaled deployments).

**Drivers:** BadgerDB (`dgraph-io/badger`), PostgreSQL (`jackc/pgx`, `lib/pq`), IPFS Datastore.

**SQL Schema (15 tables):** `sources` (data sources), `spaces` (storage spaces), `space_sources` (space-source mapping), `fs_entries` (filesystem entries), `directory_children` (directory tree), `nodes` (DAG nodes with UnixFS data), `links` (DAG edges), `uploads` (upload records), `shards` (CAR shards with digest and state), `dag_scans` (DAG traversal state), `nodes_in_shards`/`node_uploads` (node-to-shard mapping), `indexes` (ShardedDAGIndex records with PDP accept state), `shards_in_indexes`.

The schema tracks the full lifecycle of preparing files for upload: scanning filesystem entries, building UnixFS DAGs, sharding into CARs, creating indexes, and tracking upload state.

**No Terraform** -- Guppy is not deployed to cloud infrastructure.

### Etracker — Egress Tracking

Etracker is a lightweight Go service for recording egress events. It has minimal infrastructure:

**Drivers:** AWS SDK v1 + v2 (for DynamoDB/SQS access), IPFS Datastore.

**IAM:** Basic task execution permissions (defined in its deployment Terraform, which is sparse -- likely deployed via Storoku-generated infrastructure or manually).

Etracker does not define its own DynamoDB tables; it writes to the `egress-traffic-events` table defined in w3infra.

## Key Config Files

| File | Purpose |
|------|---------|
| `w3infra/sst.config.ts` | Main AWS infrastructure config |
| `w3infra/upload-api/tables/index.js` | Upload API DynamoDB schemas |
| `w3infra/billing/tables/` | Billing DynamoDB schemas |
| `w3infra/stacks/` | 13 SST stack definitions |
| `w3filecoin-infra/sst.config.js` | Filecoin pipeline infra |
| `w3filecoin-infra/packages/core/src/store/index.js` | Filecoin table schemas |
| `content-claims/sst.config.ts` | Claims service infra |
| `content-claims/packages/infra/src/lib/store/index.js` | Claims table schema |
| `freeway/wrangler.toml` | Gateway worker config |
| `reads/packages/edge-gateway/wrangler.toml` | Edge gateway with service bindings |
