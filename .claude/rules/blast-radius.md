# Blast Radius — Check Before Changing Shared Code

## EXTREME caution (15+ repos affected)
`@ucanto/core`, `@ucanto/interface`, `@ucanto/principal`, `@ucanto/transport`, `@ipld/car`

## HIGH caution (10+ repos)
`@storacha/capabilities`, `@storacha/client`, `@ucanto/server`, `@ucanto/client`, `@ipld/dag-cbor`

## Go equivalents
`go-ucanto` (12 repos), `go-libstoracha` (11 repos)

## Rules
- Adding new capabilities = safe
- Changing existing capability schemas = dangerous (check all handler + client repos)
- Before changing any package above, run: `python aidev/tools/query.py impact <package>`
- Consult `aidev/memory/architecture/shared-packages.md` for full dependency analysis
