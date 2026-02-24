---
name: impact
description: Assess blast radius of changes to packages, capabilities, or services
user_invocable: true
---

# Assess blast radius of a change

Analyze what will be affected if you change a specific package, capability, or service.

## Usage

The user will specify a package name, capability, or service to assess. For example:
- `/impact @ucanto/core`
- `/impact blob/add`
- `/impact indexing-service`

## Instructions

1. Read the argument provided by the user (`$ARGUMENTS`).
2. Determine the type of change:
   - **Package name** (starts with `@` or is a Go module path): Look up in `aidev/memory/architecture/shared-packages.md`
   - **Capability** (contains `/` like `blob/add`): Look up in `aidev/memory/architecture/spec-implementation-map.md` and check which services handle it
   - **Service/repo name**: Look up in `aidev/memory/architecture/shared-packages.md` and the root `CLAUDE.md`

3. Read the relevant architecture files:
   - `aidev/memory/architecture/shared-packages.md` — for package blast radius (JS tiers, Go modules, cross-repo dependencies)
   - `aidev/memory/architecture/spec-implementation-map.md` — for capability → handler mappings
   - `aidev/memory/architecture/infrastructure-decisions.md` — for infrastructure dependencies (DynamoDB tables, queues, buckets)

4. Report:
   - **Direct dependents**: Repos/packages that directly import this
   - **Transitive impact**: What breaks downstream
   - **Safe vs dangerous**: Is this a safe additive change or a breaking change?
   - **Testing scope**: Which repos need testing after this change
   - **Migration needs**: Does this require a coordinated rollout?

5. For capability changes specifically:
   - Which service(s) handle this capability (handler file paths)
   - Which client(s) invoke it
   - Whether the capability schema is shared across JS and Go

## Quick Reference Tiers

From shared-packages.md:
- **EXTREME (15+ repos):** @ucanto/core, @ucanto/interface, @ucanto/principal, @ucanto/transport, @ipld/car
- **HIGH (10+ repos):** @storacha/capabilities, @storacha/client, @ucanto/server, @ucanto/client, @ipld/dag-cbor
- **Go:** go-ucanto (12 repos), go-libstoracha (11 repos)

## Deep Cross-Cutting Analysis

For queries that require correlating data across repos, capabilities, infrastructure, and service graphs, use the Layer 5 query tool:

```bash
python aidev/tools/query.py impact <repo-or-package>   # Full dependency + reverse-dep + infra analysis
python aidev/tools/query.py capability <name>           # Find all repos defining/handling a capability
python aidev/tools/query.py repo <name>                 # Comprehensive repo overview
python aidev/tools/query.py graph <repo>                # Service graph edges (in/out)
```
