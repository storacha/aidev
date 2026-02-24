# Portable Agent Context: Product Brief

## The Problem

AI agent context is siloed. Every LLM and agent framework stores memory in its own format, on its own servers, with no portability:

- **Claude Code** stores memory in `.claude/` markdown files (local, not synced)
- **ChatGPT** stores memory on OpenAI's servers (proprietary, no export, no sharing)
- **Cursor** has its own rules/context system (local `.cursor/rules/`)
- **OpenClaw** has per-agent workspaces (local markdown directories)
- **Custom agents** roll their own — usually flat files or a database

When you switch tools, you start from zero. When your teammate wants to share context, you copy-paste. When your "main" agent and your "review" subagent need shared knowledge, you pass it manually.

This is the same problem Dropbox solved for files in 2008 and iCloud solved for apps in 2011 — except for AI agent memory, and with harder constraints: multiple writers (agents + humans), concurrent edits, cross-framework portability, and the need for granular access control.

## The Insight

**Markdown files are already the universal LLM interface.**

Every LLM can read markdown. Every agent framework can write files. The filesystem is the lowest common denominator — no protocol negotiation, no API integration, no format conversion. A directory of markdown files is already how Claude Code, OpenClaw, and most custom agents store context.

The missing piece isn't the format. It's **sync + merge + access control** on top of it.

## The Product

A lightweight sync engine that watches a directory of files and syncs them to a Storacha Space — decentralized, encrypted, conflict-free. Any agent on any device can read and write to the same context. Concurrent edits to the same markdown file merge automatically via CRDT.

```
Agent context directory (markdown files)
         |
    +----------+
    | sync     |  <-- watches files, CRDT merge for .md, encrypts if private
    | daemon   |  <-- UCAN delegations for access control
    +----------+
         |
    Storacha Space (content-addressed, decentralized)
         |
    +----+----+----------+----------+
    |         |          |          |
  Device 2  Device 3  Teammate   Different LLM
  (Claude)  (phone)   (granted)  (Cursor, GPT, etc.)
```

### Core capabilities

1. **File sync** — watches a directory, encodes files as content-addressed blocks, uploads to Storacha. Regular files use UnixFS (standard IPFS encoding). Bidirectional — remote changes are pulled and written locally.

2. **CRDT markdown merge** — markdown files (.md) get structural merge via RGA tree CRDT (from `@storacha/md-merge`). The markdown AST is represented as an RGA tree where every `children` array is a Replicated Growable Array. Concurrent edits at the paragraph/section level merge automatically without conflicts. This is the core differentiator.

3. **End-to-end encryption** — private spaces encrypt all content via KMS before upload. Only devices with the proper UCAN delegation can decrypt. The storage provider (Storacha) cannot read the content.

4. **Granular access control** — UCAN delegations control who can read/write. You can grant a teammate access to a shared context space, grant a subagent read-only access, or revoke access at any time. No shared accounts or passwords — cryptographic delegation.

5. **Multi-device, multi-agent, multi-user** — any number of writers can sync to the same space. The merkle clock (UCN Pail) tracks causal ordering. The CRDT merge ensures all devices converge to the same state, regardless of the order changes arrive.

## User Stories

### 1. "My AI knows me everywhere" (individual, cross-device)

> I use Claude Code on my work laptop, Cursor on my personal machine, and ChatGPT on my phone. When Claude learns something about my codebase conventions, I want Cursor to know it too. When I tell ChatGPT my preferences, I want those to be available to Claude.

**How it works:** Install the sync daemon on each device. Point it at the agent's context directory. All markdown memory files sync automatically. Each agent reads the same context on startup.

### 2. "My team's AI knows what we know" (team, shared context)

> Our team has a shared AI agent. Multiple engineers interact with it. The agent accumulates knowledge about our architecture, conventions, and decisions. We need this knowledge base to be shared, up-to-date, and conflict-free — even when two people are editing it simultaneously.

**How it works:** One person sets up a Storacha Space and runs `grant <teammate-DID>` for each team member. Each member's agent reads/writes to the synced directory. Two agents editing the same architecture notes simultaneously? The CRDT merge handles it — paragraphs added by each agent both appear, correctly ordered, no manual conflict resolution.

### 3. "I own my AI's memory" (self-custody, privacy)

> I don't want OpenAI or Anthropic or Google to own my agent's knowledge about me. I want to control where it's stored, who can access it, and be able to revoke access or export everything at any time.

**How it works:** Your context lives in your Storacha Space — content-addressed, optionally encrypted. You hold the keys (Ed25519 agent keypair + UCAN delegations). You can revoke any device's access, export all data as standard files, or switch storage providers. No vendor lock-in.

### 4. "My agents share context" (multi-agent, subagent collaboration)

> My main coding agent spawns review agents, research agents, and planning agents. These subagents need to share knowledge with the main agent — findings, decisions, progress notes — without manual copy-paste and without context window pollution.

**How it works:** Each agent gets a UCAN delegation scoped to the shared context space. Agents write findings as markdown files. The sync engine propagates changes. The main agent picks up subagent findings on the next read. The CRDT merge handles concurrent writes from multiple agents to the same file.

## Why Not Just Use...

| Alternative | What's missing |
|------------|---------------|
| **Dropbox / iCloud** | Last-write-wins on concurrent edits (silent data loss). No granular access control. Trust the provider with your data. |
| **Git** | Requires manual conflict resolution. Not real-time. Heavyweight for this use case. |
| **Syncthing** | File-level LWW (last-modified timestamp wins). No content merge. No encryption. |
| **Obsidian Sync** | Proprietary, centralized. No CRDT merge. Tied to Obsidian. |
| **A shared database** | Requires infrastructure. Not file-based (agents can't just read/write markdown). Not decentralized. |

**The gap:** No existing solution combines file-watching + structural markdown CRDT merge + end-to-end encryption + granular UCAN access control + decentralized storage. Each piece exists separately, but the composition is novel.

## Technical Foundation

### What exists today (in clawracha)

The `@storacha/clawracha` OpenClaw plugin (v0.3.15) implements the full sync engine. It's ~1,500 LOC TypeScript, split roughly 80/20 between framework-agnostic core and OpenClaw-specific glue.

**Framework-agnostic core (portable):**
- `SyncEngine` — orchestrates watch -> encode -> diff -> publish -> upload -> apply remote
- `mdsync/` — CRDT markdown merge via `@storacha/md-merge` (RGA tree on mdast)
- `handlers/` — process changes, apply pail ops, apply remote changes
- `blockstore/` — tiered LRU -> Disk -> Gateway
- `watcher.ts` — chokidar file watcher with debouncing
- `commands.ts` — init, setup, join, grant logic
- `utils/` — crypto, delegation, bundle, encoder, differ, tempcar

**OpenClaw-specific (not portable):**
- `plugin.ts` — OpenClaw plugin registration, CLI, MCP tools, HTTP handler (~300 lines)
- `utils/workspace.ts` — OpenClaw workspace path resolution

### Key dependencies

| Package | Role | Maturity |
|---------|------|----------|
| `@storacha/ucn` (1.1.1-rc.3) | Multiwriter CRDT KV store (Pail + merkle clock) | RC |
| `@storacha/md-merge` (0.9.0) | Structural markdown CRDT merge (RGA tree on mdast) | Pre-1.0 |
| `@storacha/client` (2.0.4) | Storacha upload/storage client | Stable |
| `@storacha/encrypt-upload-client` (1.1.76-rc.1) | E2E encryption via KMS | RC |
| `@web3-storage/pail` (0.6.3-rc.3) | Base sharded trie + merkle clock + CRDT layer | RC |
| `@storacha/capabilities` (2.2.0) | UCAN capability definitions | Stable |

### The two-level CRDT architecture

The system is a **product lattice** of two CRDTs:

**Level 1 — Pail (KV CRDT):** Maps file paths to CIDs. Merkle clock for causal ordering. Multiple heads = concurrent unmerged writes. Resolution = deterministic replay from common ancestor (topological sort). Last-writer-wins per key.

**Level 2 — md-merge (per markdown file):** Each markdown value is a DAG-CBOR block containing an RGA tree (the document) + an event RGA (causal history) + the latest changeset. Merge = set-union of RGA nodes with tombstone-wins. The event RGA's BFS linearization provides the comparator for ordering concurrent inserts.

Both levels satisfy the join-semilattice properties (commutative, associative, idempotent merge), so convergence is mathematically guaranteed regardless of network behavior.

### How CRDT markdown merge works

1. Markdown is parsed to mdast (standard markdown AST)
2. Every `children` array in the AST is replaced with an RGA (Replicated Growable Array)
3. Each node gets a globally unique ID (UUID + causal event reference)
4. Edits produce changesets: insert node after X, delete node Y, modify node Z
5. On concurrent writes from different devices:
   - Find common ancestor via merkle clock DAG traversal
   - Replay each branch's changesets in deterministic causal order
   - Merge RGA node sets (union) — concurrent inserts at the same position are ordered by the event comparator
6. Result: all devices converge to the same document, with all edits preserved

**Granularity:** operates at the mdast node level (paragraphs, list items, headings, code blocks). Two agents adding different paragraphs to the same file merge perfectly. Two agents editing the *text within* the same paragraph — one wins (the node is replaced). This is the right tradeoff for agent context files, where edits are typically "add a section" not "modify a word."

### Comparison to mainstream CRDTs

| | Yjs / Automerge | md-merge (Storacha) |
|---|---|---|
| **Merge granularity** | Character-level | AST node level (paragraph, list item) |
| **Transport** | Dedicated sync protocol | Content-addressed (any network) |
| **Persistence** | Separate storage layer | The DAG is the storage |
| **Auth** | Application-layer | Protocol-layer (UCAN) |
| **Encryption** | Application-layer | Built-in (KMS) |
| **Best for** | Real-time collaborative text editing | Agent workspace sync, knowledge base merge |

Mainstream CRDTs (Yjs, Automerge, Loro) are better for real-time character-level collaborative editing (Google Docs-style). The Storacha approach is better for asynchronous, multi-agent, multi-device knowledge sync where structural merge (paragraphs, sections) is the right granularity.

## Generalization Path

### Phase 1: Extract the core library

Extract the framework-agnostic sync engine from clawracha into a standalone package:

**`@storacha/workspace-sync`** (or `@storacha/context-sync`):
- `SyncEngine` — the core sync loop
- `mdsync/` — CRDT markdown merge
- `handlers/` — process, apply, remote
- `blockstore/` — tiered storage
- `watcher.ts` — file watcher
- `commands.ts` — init, setup, join, grant (without OpenClaw workspace resolution)
- `utils/` — all utilities

**Standalone CLI:**
```bash
storacha-sync init           # Generate agent identity
storacha-sync setup          # Login, create space, start syncing
storacha-sync join <bundle>  # Join existing workspace from delegation bundle
storacha-sync grant <DID>    # Grant another device/user access
storacha-sync status         # Show sync state
```

No framework dependency. Works with any directory of files.

### Phase 2: Framework adapters

Thin adapters (~50-100 lines each) that map framework-specific context locations to the sync engine:

- **OpenClaw adapter** — the existing clawracha plugin, rewritten as a thin wrapper
- **Claude Code adapter** — watches `.claude/` directories (CLAUDE.md, memory files, project instructions)
- **Cursor adapter** — watches `.cursor/rules/` and `.cursorrules`
- **Generic adapter** — watches any user-specified directory

Each adapter answers two questions: "where are the context files?" and "how do I register tools/commands in this framework?"

### Phase 3: Ecosystem

- MCP server that exposes sync status and manual sync trigger as tools (works with any MCP-compatible agent)
- Web dashboard for managing spaces, delegations, and viewing sync history
- Mobile companion for viewing/editing context on the go

## Market Position

### What this is

**Portable, shareable, conflict-free AI memory.**

Your agent's context follows you across LLMs, devices, and frameworks. Share it with teammates via cryptographic delegation. Own your data — encrypted, decentralized, no vendor lock-in.

### What this is not

- Not a real-time collaborative editor (use Yjs/Automerge for that)
- Not a database (use cr-sqlite for structured data)
- Not a messaging protocol (use MCP/A2A for agent communication)

### The moat

1. **md-merge CRDT** — structural markdown merge is unique. Nobody else offers conflict-free merge at the AST level for markdown files on content-addressed storage.
2. **UCAN delegation model** — granular, cryptographic, revocable access control without shared accounts. This is fundamentally different from "share a folder link."
3. **Content-addressed persistence** — every version of every file has a CID. Tamper-evident, deduplicatable, verifiable. The sync protocol is transport-agnostic because the data is self-describing.
4. **Storacha infrastructure** — Filecoin-backed persistence, R2/S3 hot storage, IPFS gateway retrieval. The storage layer is production-grade.

### Adjacent opportunities

- **"Memory marketplace"** — publish curated context packs (coding conventions, framework guides, domain knowledge) as Storacha spaces. Others subscribe via delegation.
- **"Context-as-a-service"** — API for applications to store/retrieve/merge agent context without running the sync daemon.
- **"Audit trail"** — content-addressed history means every edit to agent memory is traceable. Important for enterprise compliance.

## Open Questions

1. **Naming:** Is this "workspace sync", "context sync", "agent memory", or something else? The name determines the market perception.
2. **Pricing model:** Free for public spaces (drives storage usage), paid for private (encrypted) spaces? Per-space fee? Hannah suggested "$1 upcharge per space."
3. **Non-markdown files:** Binary files (images, PDFs, embeddings) sync fine via UnixFS but don't get CRDT merge. Is that sufficient, or do we need structured CRDT for JSON/YAML config files too?
4. **Latency expectations:** File-watching has 500ms debounce + upload time. Is this fast enough for the target use cases? Agent memory writes are typically infrequent (minutes between writes, not seconds).
5. **Garbage collection:** RGA tombstones and merkle clock history grow unboundedly. What's the compaction strategy for long-lived context spaces?
6. **Intra-paragraph merge:** The current md-merge operates at AST node granularity. If two agents edit the same paragraph, one wins. Is this a real user problem or a theoretical concern? (For agent memory files, likely theoretical — agents add sections, they don't edit the same sentence.)
