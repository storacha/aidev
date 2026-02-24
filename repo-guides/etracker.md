# etracker

Go service for egress tracking. Receives `space/egress/track` invocations from storage nodes, consolidates, and reports for billing.

## Quick Reference

```bash
make build              # go build -o ./etracker ./cmd/etracker
make test               # go test -v ./...
```

## Structure

```
cmd/
  etracker/
    main.go             # Entry point
    start.go            # Start server command
  client/
    track.go            # CLI client for space/egress/track
internal/
  server/
    methods.go          # UCAN service methods
  consolidator/
    consolidator.go     # space/egress/consolidate implementation
```

## UCAN Capabilities

| Capability | Handler | Purpose |
|---|---|---|
| `space/egress/track` | `server/methods.go` | Receive batch of retrieval receipts |
| `space/egress/consolidate` | `consolidator/` | Aggregate egress data for billing |

## Key Patterns

- Uses `go-ucanto` for UCAN server
- Storage nodes batch `space/content/retrieve` receipts and send via `space/egress/track`
- Consolidation runs periodically, aggregating per-space egress data
- Separate from Freeway's JS egress tracking (which uses `space/content/serve/egress/record` via Cloudflare Queue)

## What Breaks If You Change Things Here

- Egress data format changes affect billing accuracy
- Must stay aligned with Piri's egress tracking output
