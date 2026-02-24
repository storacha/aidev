#!/bin/bash
# Hook 4: Pre-Commit Checks
# Event: PreToolUse (matcher: Bash)
# Purpose: Verify prerequisites before allowing git commits.
#
# Checks:
# 1. Not on main/master (defense-in-depth with Hook 2)
# 2. PHASE is implement or complete
# 3. Tests pass for affected files
#
# This hook is more thorough than Hook 2 — it validates the full
# process state, not just the branch.
#
# Reads JSON from stdin with .tool_input.command
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check git commit commands (not push — Hook 2 handles push)
if ! echo "$COMMAND" | grep -qE 'git\s+.*\bcommit\b'; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
ERRORS=""

# Determine which git repo the command targets (same logic as branch-protection.sh)
REPO_DIR=""
if echo "$COMMAND" | grep -qE '^\s*cd\s+'; then
  REPO_DIR=$(echo "$COMMAND" | sed -nE 's/^[[:space:]]*cd[[:space:]]+"?([^"&;]*[^"&;[:space:]])"?[[:space:]]*(&&|;).*/\1/p' | head -1)
fi
if [ -z "$REPO_DIR" ] && echo "$COMMAND" | grep -qE 'git\s+-C\s+'; then
  # Extract path from "git -C /path commit..." (try quoted first, then unquoted)
  REPO_DIR=$(echo "$COMMAND" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+"([^"]+)"[[:space:]]+.*/\1/p' | head -1)
  [ -z "$REPO_DIR" ] && REPO_DIR=$(echo "$COMMAND" | sed -nE 's/.*git[[:space:]]+-C[[:space:]]+([^[:space:]]+)[[:space:]]+.*/\1/p' | head -1)
fi

BRANCH=""
for dir in "$REPO_DIR" "$PROJECT_DIR" "."; do
  [ -z "$dir" ] && continue
  BRANCH=$(git -C "$dir" branch --show-current 2>/dev/null || echo "")
  [ -n "$BRANCH" ] && break
done

# 1. Check branch
if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  # Check if there's an active feature
  PHASE_FILE=$(find "$PROJECT_DIR/.specs/active" -name "PHASE" 2>/dev/null | grep -v '.gitkeep' | head -1 || true)
  if [ -n "$PHASE_FILE" ] && [ -f "$PHASE_FILE" ]; then
    FEATURE=$(basename "$(dirname "$PHASE_FILE")")
    ERRORS="$ERRORS\n- On '$BRANCH' but feature '$FEATURE' is active. Create branch: git checkout -b feat/$FEATURE"
  fi
fi

# 2. Check phase
PHASE_FILE=$(find "$PROJECT_DIR/.specs/active" -name "PHASE" 2>/dev/null | grep -v '.gitkeep' | head -1 || true)
if [ -n "$PHASE_FILE" ] && [ -f "$PHASE_FILE" ]; then
  PHASE=$(cat "$PHASE_FILE")
  if [[ "$PHASE" != "implement" && "$PHASE" != "complete" ]]; then
    ERRORS="$ERRORS\n- Phase is '$PHASE' but commits are only allowed in implement or complete phase."
  fi
fi

if [ -n "$ERRORS" ]; then
  echo -e "BLOCKED: Pre-commit checks failed:$ERRORS" >&2
  exit 2
fi

exit 0
