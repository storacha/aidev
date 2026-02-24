# aidev — Storacha AI Development Process

AI-powered development tooling for the [Storacha](https://storacha.network) codebase — 82 repositories, JS + Go, building a decentralized storage network on UCAN-based RPC.

Clone this repo into your project directory, run `/setup` inside Claude, and you're ready to go.

## Quick Start

```bash
cd ~/storacha                # your project directory (create it if new)
git clone https://github.com/storacha/aidev.git
cd aidev
claude                       # start Claude Code inside aidev
```

Inside Claude, run:
```
/setup                       # creates symlinks in parent directory
```

Then restart Claude from the project root:
```bash
cd ..
claude                       # now running with full process
```

Clone repos alongside `aidev/` as needed:
```bash
gh repo clone storacha/upload-service
gh repo clone storacha/freeway
```

## Requirements

- macOS or Linux
- bash 3.1+ (macOS default works)
- git 2.x+
- jq 1.6+ (`brew install jq` / `apt install jq`)
- python 3.8+ (for query tool and scanners)
- gh (GitHub CLI, optional — for repo cloning and PR workflows)

## How It Works

The dev runs `claude` from the project root (e.g., `~/storacha/`). Three symlinks wire Claude Code to aidev's process files:

| Symlink | Target | Purpose |
|---------|--------|---------|
| `.claude` | `aidev/.claude` | Hooks, rules, skills, settings |
| `CLAUDE.md` | `aidev/CLAUDE.md` | Root instructions + knowledge routing |
| `.specs` | `aidev/.specs` | Feature workflow templates + state |

Working repos are siblings of `aidev/` — clone them directly into the project root.

## Directory Layout

```
~/storacha/                          ← project root, run `claude` here
├── .claude → aidev/.claude          ← symlink
├── CLAUDE.md → aidev/CLAUDE.md      ← symlink
├── .specs → aidev/.specs            ← symlink
├── aidev/                           ← this repo
│   ├── .claude/                     # Hooks, rules, skills, settings
│   ├── CLAUDE.md                    # Root instructions
│   ├── AIPIP/                       # Process improvement proposals
│   ├── memory/                      # Domain knowledge base
│   ├── repo-guides/                 # Per-repo AI guides (21 repos)
│   ├── data/                        # Scanner data (JSON)
│   ├── tools/                       # Query tool
│   ├── scripts/                     # Scanners
│   ├── research/                    # Research reports
│   ├── docs/                        # Strategy docs
│   └── .specs/                      # Templates + workspace state
├── upload-service/                  ← working repo
├── freeway/                         ← working repo
├── piri/                            ← working repo
└── ...
```

## Knowledge System

| Layer | What | Where | Loaded |
|-------|------|-------|--------|
| 1 | Root instructions — architecture, conventions, routing table | `CLAUDE.md` | Always |
| 2 | Deep knowledge — 12 tech patterns, 5 flow traces, 3 architecture docs | `aidev/memory/` | On demand |
| 3 | Per-repo guides — 21 repos with service-specific context | `aidev/repo-guides/` | When working in a repo |
| 4 | Slash commands — `/dev`, `/trace`, `/impact`, `/review` | `.claude/skills/` | On invocation |
| 5 | Query tool — cross-cutting queries over scanner data | `aidev/tools/query.py` | On invocation |

## Updating

```bash
cd aidev && git pull
# Process changes are active immediately — symlinks still point to the right place
```

## Scanner Data

Pre-computed structural data from scanning all 82 repos:

| File | Content |
|------|---------|
| `aidev/data/api-surface-map.json` | 175 UCAN capabilities, 231 service graph edges |
| `aidev/data/infrastructure-map.json` | DynamoDB tables, R2/S3 buckets, SQS queues, 57 SQL schemas |
| `aidev/data/product-map.json` | 82 repos with roles, deps, tech stack, 15 products |

```bash
python aidev/tools/query.py capability blob/add     # Who defines/handles a capability
python aidev/tools/query.py impact indexing-service  # Full dependency + infra analysis
python aidev/tools/query.py infra freeway            # Infrastructure resources for a repo
python aidev/tools/query.py repo piri                # Comprehensive repo overview
```

## Process Governance (AIPIPs)

Changes to the AI development process (rules, hooks, skills) require an AIPIP (AI Process Improvement Proposal). See [AIPIP/README.md](AIPIP/README.md) for the format and team PR flow.
