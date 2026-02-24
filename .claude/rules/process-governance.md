# Process Governance — AIPIP Required for Process Changes

## Protected Files

The following files define the AI development process. They MUST NOT be modified without an accepted AIPIP:

- `.claude/rules/*.md` — workflow rules
- `.claude/skills/*/SKILL.md` — skill definitions
- `.claude/hooks/*.sh` — enforcement hook scripts
- `.claude/hooks/*.md` — hook agent prompts
- `.claude/settings.json` — hook wiring configuration

## Before Modifying Any Protected File

1. Check that a relevant AIPIP exists in `AIPIP/` with status `accepted`
2. If no AIPIP exists, **STOP** and tell the user:
   > "This requires a process change. I need to write an AIPIP first — see `AIPIP/README.md` for the format. Want me to draft one?"
3. Do NOT modify the file until the user accepts the AIPIP

## Exception

Creating or editing AIPIP documents (`AIPIP/AIPIP-*.md`) and updating `AIPIP/README.md` is always allowed — these are the proposal mechanism itself.

## Decision Tree

```
User asks for process change
  → "This is a process change. I need to write an AIPIP first."
  → Draft AIPIP-NNNN as proposed
  → Present to user for review
  → User accepts → Update status to accepted
  → Write change token: .claude/.process-change-token (contains AIPIP ID)
  → Implement the changes to process files
  → Update AIPIP change log
  → Delete the change token
```

## Change Token

The `process-guard.sh` hook blocks writes to protected files unless `.claude/.process-change-token` exists. This token is a simple text file containing the AIPIP ID (e.g., `AIPIP-0007`).

- Write the token AFTER the user accepts the AIPIP, BEFORE modifying process files
- Delete the token AFTER all process changes are complete
- The token file itself is always writable (not protected)

## Enforcement

This rule is enforced by `process-guard.sh` (Tier 2 hook). The hook blocks writes to protected files unless the change token exists.

## Rationale

AIPIP-0004 established the governance model. AIPIP-0007 enforces it. Without enforcement, the AI modifies process files under task pressure ("just do it") and the change history becomes untraceable.
