---
id: AIPIP-0011
title: Create storacha/aidev repo for team distribution
status: accepted
created: 2026-02-24
created-by: claude
---

# AIPIP-0011: Create storacha/aidev Repo for Team Distribution

## Problem

The AI development process (rules, skills, hooks, knowledge base, AIPIPs) lives in a single developer's local workspace (`storacha-analysis/`). Other developers cannot use it. The process needs to be distributed as a private repo that any Storacha team member can clone and use immediately.

Key issues:
1. **No distribution mechanism** — everything is local to one developer
2. **Per-repo CLAUDE.md files are trapped** — 21 repo guides live inside gitignored `repos/` directories and aren't committed
3. **Workspace state mixed with process** — `.specs/` feature state, `.process-change-token`, auto-memory are local concerns mixed with shared process files
4. **AIPIP governance is single-player** — the token-based flow works for one developer but needs a PR-based flow for a team

## Proposal

### 1. Model: aidev as sibling + symlinks

The dev's project root (e.g., `~/storacha/`) contains working repos as direct children. `aidev` is cloned alongside them. Three symlinks at the project root wire Claude Code to the process files.

**Why symlinks?** Claude Code loads `.claude/settings.json` and `CLAUDE.md` from the directory where `claude` is launched. The dev launches `claude` from the project root, so these must resolve there. Symlinks into `aidev/` achieve this without duplicating files.

**New dev:**
```bash
mkdir ~/storacha && cd ~/storacha
git clone git@github.com:storacha/aidev.git
ln -s aidev/.claude . && ln -s aidev/CLAUDE.md . && ln -s aidev/.specs .
claude
# clone repos as needed
gh repo clone storacha/upload-service
gh repo clone storacha/freeway
```

**Existing dev (repos already at `~/storacha/`):**
```bash
cd ~/storacha
git clone git@github.com:storacha/aidev.git
ln -s aidev/.claude . && ln -s aidev/CLAUDE.md . && ln -s aidev/.specs .
claude    # repos already here, ready to go
```

### 2. Directory layout

```
~/storacha/                          ← project root, dev runs `claude` here
├── .claude → aidev/.claude          ← symlink (hooks, rules, skills, settings)
├── CLAUDE.md → aidev/CLAUDE.md      ← symlink (root instructions)
├── .specs → aidev/.specs            ← symlink (templates + workspace state)
├── aidev/                           ← process repo (storacha/aidev)
│   ├── .git/
│   ├── .gitignore
│   ├── .claude/                     # Process configuration
│   │   ├── rules/                   # Workflow rules
│   │   ├── skills/                  # Skills (/dev, /review, /trace, etc.)
│   │   ├── hooks/                   # Enforcement hooks
│   │   └── settings.json            # Hook wiring
│   ├── CLAUDE.md                    # Root instructions + knowledge routing
│   ├── README.md                    # Human onboarding guide
│   ├── AIPIP/                       # Process improvement proposals
│   ├── memory/                      # Domain knowledge base
│   │   ├── tech/                    # 12 technology pattern guides
│   │   ├── flows/                   # 5 end-to-end flow traces
│   │   └── architecture/            # 3 architecture docs
│   ├── repo-guides/                 # Per-repo AI guides
│   │   ├── upload-service.md
│   │   ├── freeway.md
│   │   ├── piri.md
│   │   └── ... (21 files)
│   ├── data/                        # Scanner data (JSON)
│   ├── tools/                       # Query tool
│   ├── scripts/                     # Scanners
│   ├── research/                    # Research reports
│   ├── docs/                        # Strategy docs
│   └── .specs/                      # Templates committed, state gitignored
│       ├── TEMPLATE-feature-brief.md
│       ├── TEMPLATE-design-doc.md
│       └── RETRO-TEMPLATE.md
├── upload-service/                  ← working repo (sibling)
├── freeway/                         ← working repo (sibling)
├── piri/                            ← working repo (sibling)
└── ...                              ← any other repos
```

**Key principle:** The project root is NOT a git repo. `aidev/` is the only git repo that contains process files. Working repos are siblings. The 3 symlinks make Claude Code find its config at the root.

### 3. Three symlinks

| Symlink | Target | Why |
|---------|--------|-----|
| `.claude → aidev/.claude` | Hooks, rules, skills, settings | Claude Code requires `.claude/` at project root |
| `CLAUDE.md → aidev/CLAUDE.md` | Root instructions | Claude Code reads CLAUDE.md from project root |
| `.specs → aidev/.specs` | Templates + workspace state | All hooks reference `$PROJECT_DIR/.specs/active/` — symlink keeps hooks unchanged |

The `.specs` symlink is the key design choice. ALL 8+ hooks reference `$PROJECT_DIR/.specs/active/` for phase tracking. Rather than updating every hook to use `$PROJECT_DIR/aidev/.specs/`, one symlink at the root keeps all hooks working unchanged.

### 4. Path convention in CLAUDE.md

Since CLAUDE.md is loaded from the project root (via symlink), all paths it references must be valid relative to the project root. Knowledge files live inside `aidev/`, so CLAUDE.md uses `aidev/` prefixed paths:

```
| Need to... | Read |
|---|---|
| Define/modify UCAN capabilities | `aidev/memory/tech/ucanto-framework.md` |
| Work with CIDs, multihash, codecs | `aidev/memory/tech/content-addressing.md` |
| ... | ... |
| Working in a specific repo | Read `aidev/repo-guides/<repo>.md` |
```

Similarly for tools:
```bash
python aidev/tools/query.py capability blob/add
python aidev/scripts/scan_api_surface.py
```

### 5. Per-repo guides (`aidev/repo-guides/`)

Move the 21 per-repo CLAUDE.md files from `repos/storacha/<repo>/CLAUDE.md` to `aidev/repo-guides/<repo>.md`. These are committed in the aidev repo and available on clone.

**How they're used:**
- CLAUDE.md routing table directs Claude to read `aidev/repo-guides/<repo>.md` when working in a specific repo
- The guides are always available — no copying needed

### 6. aidev `.gitignore`

Standard `.gitignore` — aidev tracks all its own files. Only local workspace state is ignored:

```gitignore
# Workspace state (not shared)
.specs/active/
.specs/done/
.specs/telemetry.jsonl
.specs/retro-log.md

# AIPIP governance token (never shared)
.claude/.process-change-token

# Standard ignores
.DS_Store
__pycache__/
*.pyc
.venv/
node_modules/
*.swp
.env
.env.local
```

No whitelist pattern needed — aidev is a normal repo that tracks its own files. The project root (parent directory) is not a git repo at all.

### 7. Session-resume updates

**Auto-create `.specs/` on first run:**
```bash
AIDEV_DIR="$PROJECT_DIR/aidev"
mkdir -p "$AIDEV_DIR/.specs/active" "$AIDEV_DIR/.specs/done"
```

Note: With the `.specs` symlink, `$PROJECT_DIR/.specs/active` resolves to the same path. The `mkdir -p` ensures the gitignored directories exist on first run.

**Git state scanner — scan sibling repos:**

Current: scans `$PROJECT_DIR/repos/storacha/*/`
New: scans `$PROJECT_DIR/*/` (direct child directories that are git repos)

```bash
for repo_dir in "$PROJECT_DIR"/*/; do
  [ -d "$repo_dir/.git" ] || continue
  # ... existing git status logic
done
```

This picks up any git repos cloned inside the project root, including `aidev/` itself (useful for showing uncommitted process changes).

### 8. AIPIP governance for a team

**Token stays local:**
- `.claude/.process-change-token` is gitignored — never pushed
- A dev creates it locally when implementing process changes on a branch

**PR flow for process changes:**
1. Dev branches from main in `aidev/`
2. Writes `AIPIP/AIPIP-NNNN-slug.md` with status `proposed`
3. Creates `.process-change-token` locally
4. Implements process file changes on the branch
5. Deletes token locally
6. Pushes branch, opens PR to `storacha/aidev`
   - PR includes: AIPIP doc (status: `proposed`) + implementation
7. Team reviews — comments, suggestions
8. Process owner approves PR
9. Before merge: author updates AIPIP status to `accepted` (final commit on the PR)
10. Squash-merge
11. Other devs: `cd aidev && git pull`

**Local-only adjustments:**
- A dev can modify their local copy of any process file
- They create the token locally, make changes, delete the token
- These changes stay local (not pushed) unless they open a PR
- `git pull` may produce merge conflicts — dev reconciles manually

### 9. Platform requirements

Document in README:

```
## Requirements
- macOS or Linux
- bash 3.1+ (macOS default works)
- git 2.x+
- jq 1.6+ (brew install jq / apt install jq)
- python 3.8+ (for query tool and scanners)
- gh (GitHub CLI, optional — for repo cloning and PR workflows)
```

Hooks use POSIX-compliant constructs only (`[[:space:]]` not `\s` in sed, bash 3.x compatible syntax). No platform-specific branching needed.

### 10. Update mechanism

```bash
cd aidev && git pull
# Process changes active immediately — symlinks still point to the right place
```

### 11. First-run experience

1. Dev clones `aidev` into their project directory
2. `cd aidev && claude` — starts Claude Code inside aidev
3. `/setup` — runs `setup.sh` which creates the 3 symlinks in the parent directory
4. Dev exits claude, `cd ..`, runs `claude` from project root — full process active
5. `session-resume.sh` creates `.specs/active/` and `.specs/done/` if missing
6. Dev clones repos alongside `aidev/` as needed
7. If `jq` is missing, hooks fail with a clear error message

**`setup.sh`** — POSIX shell script in the aidev root. Creates the 3 symlinks in the parent directory. Idempotent (safe to re-run). Warns if a non-symlink file already exists at a target path.

**`/setup` skill** — Claude Code skill that runs `setup.sh` and guides the user through restarting from the project root.

## Alternatives Considered

### A. Aidev IS the working directory (repos cloned inside)
Dev clones aidev as the project root, repos go inside. Uses whitelist `.gitignore` to only track aidev files. Rejected — existing devs have repos at `~/storacha/` already; making that directory a git repo and using whitelist gitignore is invasive. Also mixes two git histories (aidev + each repo) in confusing ways when `git status` runs from root.

### B. Aidev as sibling, no symlinks
Requires the dev to run `claude` from `aidev/` and access repos via `../`. Rejected — unnatural workflow. Claude Code loads config from the launch directory, not from a child directory.

### C. Inject process into existing repos (per-repo .claude/)
Rejected — Claude Code loads hooks from the project root's `.claude/`. Would need to maintain `.claude/` in every repo checkout.

### D. No setup script
Originally proposed documenting 3 symlinks as a one-liner in the README. Revised — a `setup.sh` + `/setup` skill is more user-friendly and self-documenting. The script is trivial (creates 3 symlinks) and the skill guides the user through the flow.

### E. Separate process repo from knowledge repo
Premature — the knowledge base is tightly coupled to the process (CLAUDE.md routing table, repo-guides). Split later if the process proves reusable beyond Storacha.

### F. More symlinks (memory/, AIPIP/, repo-guides/, etc.)
Rejected — only 3 things need to resolve at the project root (`.claude/`, `CLAUDE.md`, `.specs/`). Everything else is referenced with `aidev/` prefix in CLAUDE.md. Fewer symlinks = less to break.

## Impact

### New files

| File | Purpose |
|------|---------|
| `repo-guides/*.md` | 21 per-repo AI guides (extracted from gitignored repos/) |
| `setup.sh` | Creates 3 symlinks in parent directory (first-run setup) |
| `.claude/skills/setup/SKILL.md` | `/setup` skill — runs setup.sh and guides user |

### Modified files

| File | Change |
|------|--------|
| `.claude/hooks/session-resume.sh` | Add `mkdir -p` for first-run, scan `$PROJECT_DIR/*/` instead of `repos/storacha/` |
| `CLAUDE.md` | Prefix all knowledge/tool paths with `aidev/`, add `repo-guides/` to routing table |
| `README.md` | Rewrite for team audience — quick start (clone + symlinks), layout, requirements |
| `AIPIP/README.md` | Add team PR flow to "How to Propose a Change" section |

### Structural changes

| Change | Description |
|--------|-------------|
| `.specs/` split | Templates committed, workspace state (active/done/telemetry) gitignored |
| Per-repo guides extracted | 21 files from `repos/storacha/<repo>/CLAUDE.md` → `repo-guides/<repo>.md` |
| Path prefix convention | All CLAUDE.md paths reference `aidev/memory/`, `aidev/repo-guides/`, `aidev/data/`, etc. |
| Repo layout | Repos are siblings of `aidev/` at project root, not nested inside it |
| 3 symlinks | `.claude → aidev/.claude`, `CLAUDE.md → aidev/CLAUDE.md`, `.specs → aidev/.specs` |
| Repo created | `storacha/aidev` (private) on GitHub |

### What does NOT change

| Unchanged | Why |
|-----------|-----|
| All hook scripts (except session-resume) | `.specs` symlink resolves `$PROJECT_DIR/.specs/` correctly — no code changes needed |
| `.claude/settings.json` | Loaded from symlinked `.claude/` — works as-is |
| `.claude/rules/*.md` | No path references that need updating |
| Skill definitions | Referenced via `.claude/skills/` which is symlinked |

## Implementation Order

1. Extract per-repo CLAUDE.md files to `repo-guides/`
2. Create aidev `.gitignore` (standard, not whitelist)
3. Update `session-resume.sh` — first-run mkdir + sibling repo scanning
4. Update `CLAUDE.md` — prefix all knowledge/tool paths with `aidev/`
5. Rewrite `README.md` for team audience (clone + symlinks quickstart)
6. Update `AIPIP/README.md` with team PR flow
7. Create `storacha/aidev` repo on GitHub, push

## Change Log

| Date | Change |
|------|--------|
| 2026-02-24 | Initial proposal |
| 2026-02-24 | Revised: removed setup.sh, sibling repo model |
| 2026-02-24 | Revised: aidev IS the working directory, repos cloned inside, whitelist .gitignore |
| 2026-02-24 | Revised: Option B — aidev as sibling with 3 symlinks. Repos are siblings at project root. `.specs` symlink keeps all hooks unchanged. CLAUDE.md paths use `aidev/` prefix. |
| 2026-02-24 | Accepted and implemented. Changes: extracted 21 repo-guides, updated session-resume.sh (first-run mkdir + sibling scanning), prefixed all CLAUDE.md paths with `aidev/`, rewrote README.md for team audience, added team PR flow to AIPIP/README.md. Also updated all skill definitions (discover-repo, impact, trace, spec, new-capability), rules (blast-radius.md), and docs (knowledge-strategy.md, Knowledge-Base-Guide.md, AI-Dev-Process-Guide.md, memory/MEMORY.md) with `aidev/` prefixed paths. |
| 2026-02-24 | Added `setup.sh` + `/setup` skill for first-run onboarding. Reversed earlier "no setup script" decision — a script + skill is more user-friendly than documenting symlink commands. Updated README with new flow: clone → cd aidev → claude → /setup → restart from parent. |
