---
name: trace
description: Load an end-to-end flow trace into context for understanding system paths before making changes
user_invocable: true
---

# Trace an end-to-end flow

Load a flow trace into context to understand the complete path through the system before making changes.

## Usage

The user will specify a flow name. Match it to one of these trace files:

| Flow | File | Description |
|------|------|-------------|
| upload | `aidev/memory/flows/upload-flow.md` | Client → blob/add → R2 → index/add → IPNI → upload/add |
| retrieval | `aidev/memory/flows/retrieval-flow.md` | HTTP request → Freeway (26 middlewares) → indexing-service → blob-fetcher → R2 |
| auth | `aidev/memory/flows/auth-flow.md` | Email → access/authorize → session → delegation chain → capability invocation |
| filecoin | `aidev/memory/flows/filecoin-deal-flow.md` | storefront → aggregator → dealer → deal-tracker (JS) + PDP (Go) |
| egress | `aidev/memory/flows/egress-tracking-flow.md` | Freeway → queue → egress-consumer → upload-api → usage/billing |

## Instructions

1. Read the argument provided by the user (e.g., `$ARGUMENTS`).
2. Match it to the closest flow name from the table above. Accept partial matches and aliases (e.g., "upload" or "up", "retrieval" or "retrieve" or "gateway", "filecoin" or "fil" or "deal", "auth" or "login", "egress" or "billing").
3. Read the corresponding flow trace file from the `aidev/memory/flows/` directory.
4. Present a concise summary of the flow, highlighting:
   - The step-by-step path through services
   - Which repos/files handle each step
   - Which UCAN capabilities are involved
   - Key decision points and error paths
5. If the user is about to make a change, identify which steps in the flow will be affected.

If no flow name is provided, list all available flows and ask which one to load.
