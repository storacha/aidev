# Go Conventions

## Imports
- ucanto: `github.com/storacha/go-ucanto`
- Shared libraries: `github.com/storacha/go-libstoracha`
- File naming: snake_case

## Patterns
- Service methods: `server.WithServiceMethod("domain/verb", server.Provide(cap, handler))`
- Capabilities: `validator.NewCapability("domain/verb", schema, reader, derives)`
- Results: `result.Result[O,X]` — same discriminated union as JS
- Error handling: `result.Ok(value)` or `result.Error(failure)`

## Testing
- Framework: testify (`assert`, `require`, `suite`)
- Mocks: mockery-generated mocks
- Fixtures: ed25519 test signers (same deterministic DIDs as JS)

## Key Go Repos
- `piri` — storage node (PDP proofs, retrieval)
- `indexing-service` — content routing (IPNI + claims)
- `etracker` — egress tracking
- `go-libstoracha` — shared Go libraries
- `go-ucanto` — Go ucanto implementation
