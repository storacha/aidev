---
name: spec
description: Show spec-to-implementation mapping with capabilities, handler locations, and divergences
user_invocable: true
---

# Load spec-to-implementation mapping

Show how a W3 protocol spec maps to actual code — what's implemented, what's missing, and where the divergences are.

## Usage

The user will specify a spec name. For example:
- `/spec w3-blob`
- `/spec filecoin`
- `/spec content-serve`

## Instructions

1. Read the argument provided by the user (`$ARGUMENTS`).
2. Read `aidev/memory/architecture/spec-implementation-map.md` which contains the full mapping of all 24 specs.
3. Find the matching spec entry. Accept partial matches (e.g., "blob" matches "w3-blob", "filecoin" matches "w3-filecoin").
4. Present:
   - **Spec name and purpose** (1-2 lines)
   - **Capabilities defined in spec** with implementation status (implemented/missing/partial)
   - **Handler locations** (file paths for each implemented capability)
   - **Divergences** from spec (if any — the map documents 9 key divergences)
   - **Implementing repos** (which repos contain the code)

5. If the user wants the full spec text, read it from the `specs/` repo (the spec files are at `specs/w3-*.md`).

6. If no spec name is provided, list all 24 specs with their implementation status summary.

## Available Specs

The 24 specs are in the `specs/` repo:
w3-access, w3-account, w3-blob, w3-filecoin, w3-index, w3-session, w3-space, w3-store, w3-subscription, w3-upload, w3-usage, w3-plan, w3-provider, w3-consumer, w3-rate-limit, w3-admin, w3-console, w3-revocations-check, content-serve-auth, did-mailto, ucan-conclude, w3-ucan, and others.
