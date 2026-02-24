#!/bin/bash
# Hook 2: Branch Protection
# Event: PreToolUse (matcher: Bash)
# Purpose: Block git commit/push on main/master when a feature is active.
#
# Reads JSON from stdin with .tool_input.command
# Exit 0 = allow, Exit 2 = block (stderr fed back to model)

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check bash commands that involve git commit or push
if ! echo "$COMMAND" | grep -qE 'git\s+.*\b(commit|push)\b'; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

# Determine which git repo the command targets.
# The Bash tool may cd into a sub-repo (e.g., repos/storacha/guppy/).
# Try to extract the working directory from the command itself.
REPO_DIR=""
if echo "$COMMAND" | grep -qE '^\s*cd\s+'; then
  # Extract path from "cd /path && git commit..."
  REPO_DIR=$(echo "$COMMAND" | sed -nE 's/^[[:space:]]*cd[[:space:]]+"?([^"&;]*[^"&;[:space:]])"?[[:space:]]*(&&|;).*/\1/p' | head -1)
fi
if [ -z "$REPO_DIR" ] && echo "$COMMAND" | grep -qE 'git\s+-C\s+'; then
  # Extract path from "git -C /path commit..." (try quoted first, then unquoted)
  REPO_DIR=$(echo "$COMMAND" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+"([^"]+)"[[:space:]]+.*/\1/p' | head -1)
  [ -z "$REPO_DIR" ] && REPO_DIR=$(echo "$COMMAND" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+([^[:space:]]+)[[:space:]]+.*/\1/p' | head -1)
fi

# Try repo dir first, then project dir, then cwd
BRANCH=""
for dir in "$REPO_DIR" "$PROJECT_DIR" "."; do
  [ -z "$dir" ] && continue
  BRANCH=$(git -C "$dir" branch --show-current 2>/dev/null || echo "")
  [ -n "$BRANCH" ] && break
done

if [[ "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
  exit 0
fi

# Check if there's an active feature
PHASE_FILE=$(find "$PROJECT_DIR/.specs/active" -name "PHASE" 2>/dev/null | grep -v '.gitkeep' | head -1 || true)

if [ -z "$PHASE_FILE" ] || [ ! -f "$PHASE_FILE" ]; then
  # No active feature — still warn but don't block
  # (Tier 0 changes are allowed on main)
  exit 0
fi

FEATURE=$(basename "$(dirname "$PHASE_FILE")")

cat >&2 <<EOF
BLOCKED: Cannot commit/push to '$BRANCH' while feature '$FEATURE' is active.

Create a feature branch first:
  git checkout -b feat/$FEATURE

Then commit your changes there.
EOF
exit 2
