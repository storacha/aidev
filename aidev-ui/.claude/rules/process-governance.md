# Process Governance — AIPIP-UI Required for Process Changes

## Protected Files

The following files define the fullstack UI development process. They MUST NOT be modified without an accepted AIPIP-UI:

- `aidev-ui/.claude/rules/*.md` — workflow rules
- `aidev-ui/.claude/skills/*/SKILL.md` — skill definitions
- `aidev-ui/.claude/hooks/*.sh` — enforcement hook scripts
- `aidev-ui/.claude/settings.json` — hook wiring configuration

## Before Modifying Any Protected File

1. Check that a relevant AIPIP-UI exists in `aidev-ui/aipip-ui/` with status `accepted`
2. If no AIPIP-UI exists, **STOP** and tell the user:
   > "This requires a process change. I need to write an AIPIP-UI first. Want me to draft one?"
3. Do NOT modify the file until the user accepts the AIPIP-UI

## Exception

Creating or editing AIPIP-UI documents (`aipip-ui/AIPIP-UI-*.md`) and `aipip-ui/README.md` is always allowed.

## Change Token

The `process-guard.sh` hook blocks writes to protected files unless `.claude/.process-change-token` exists. Write the token AFTER user accepts, delete AFTER changes are complete.
