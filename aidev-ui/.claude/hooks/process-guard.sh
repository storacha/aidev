#!/bin/bash
# Process Change Guard Hook (PreToolUse: Edit|Write)
# Block modifications to process files unless a change token exists.
#
# Protected paths:
#   .claude/rules/*.md
#   .claude/skills/*/SKILL.md
#   .claude/hooks/*.sh
#   .claude/hooks/*.md
#   .claude/settings.json
#
# Always allowed:
#   aipip-ui/AIPIP-UI-*.md (proposal documents)
#   aipip-ui/README.md (registry)
#   .claude/.process-change-token (the token itself)
#
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

[ -z "$FILE_PATH" ] && exit 0

# Always allow AIPIP-UI documents, registry, and the token file itself
[[ "$FILE_PATH" == */aipip-ui/AIPIP-UI-*.md ]] && exit 0
[[ "$FILE_PATH" == */aipip-ui/README.md ]] && exit 0
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
  exit 0
fi

# No token — block
cat >&2 <<EOF
BLOCKED: Modifying process file requires an accepted AIPIP-UI.

File: $FILE_PATH

Before modifying it, you must:
  1. Write an AIPIP-UI proposal in aipip-ui/AIPIP-UI-NNNN-slug.md
  2. Get user approval (status: accepted)
  3. Write the change token: .claude/.process-change-token
  4. Then implement the changes
  5. Delete the token when done

See aipip-ui/README.md for the format.
EOF
exit 2
