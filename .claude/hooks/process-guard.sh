#!/bin/bash
# Hook: Process Change Guard
# Event: PreToolUse (matcher: Edit|Write)
# Purpose: Block modifications to process files unless a change token exists.
#
# Protected paths:
#   .claude/rules/*.md
#   .claude/skills/*/SKILL.md
#   .claude/hooks/*.sh
#   .claude/hooks/*.md
#   .claude/settings.json
#
# Always allowed:
#   AIPIP/AIPIP-*.md (proposal documents)
#   AIPIP/README.md (registry)
#   .claude/.process-change-token (the token itself)
#
# Flow:
#   1. Agent writes AIPIP, user accepts
#   2. Agent writes .claude/.process-change-token with AIPIP ID
#   3. Agent modifies process files (hook sees token, allows)
#   4. Agent deletes token when done
#
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

[ -z "$FILE_PATH" ] && exit 0

# Always allow AIPIP documents, registry, and the token file itself
[[ "$FILE_PATH" == */AIPIP/AIPIP-*.md ]] && exit 0
[[ "$FILE_PATH" == */AIPIP/README.md ]] && exit 0
[[ "$FILE_PATH" == */.claude/.process-change-token ]] && exit 0

# Check if this is a protected process file
IS_PROTECTED=false

case "$FILE_PATH" in
  */.claude/rules/*.md)        IS_PROTECTED=true ;;
  */.claude/skills/*/SKILL.md) IS_PROTECTED=true ;;
  */.claude/hooks/*.sh)        IS_PROTECTED=true ;;
  */.claude/hooks/*.md)        IS_PROTECTED=true ;;
  */.claude/settings.json)     IS_PROTECTED=true ;;
esac

[ "$IS_PROTECTED" = "false" ] && exit 0

# This is a protected file — check for change token
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
TOKEN_FILE="$PROJECT_DIR/.claude/.process-change-token"

if [ -f "$TOKEN_FILE" ]; then
  # Token exists — allow the change
  exit 0
fi

# No token — block
cat >&2 <<EOF
BLOCKED: Modifying process file requires an accepted AIPIP.

File: $FILE_PATH

This file is protected by process governance (AIPIP-0007).
Before modifying it, you must:
  1. Write an AIPIP proposal in AIPIP/AIPIP-NNNN-slug.md
  2. Get user approval (status: accepted)
  3. Write the change token: .claude/.process-change-token
  4. Then implement the changes
  5. Delete the token when done

See AIPIP/README.md for the AIPIP format.
EOF
exit 2
