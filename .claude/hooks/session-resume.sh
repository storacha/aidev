#!/bin/bash
# Hook 1: Session Resume
# Event: SessionStart (startup, resume, compact)
# Purpose: Re-inject active feature state into context at session boundaries.
#
# This is the #1 fix for session continuity. Without it, a new/resumed session
# has no idea what phase it's in, what tasks are done, or what branch it's on.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

# Ensure workspace directories exist (first-run)
mkdir -p "$PROJECT_DIR/.specs/active" "$PROJECT_DIR/.specs/done"

# Find active feature PHASE file
PHASE_FILE=$(find "$PROJECT_DIR/.specs/active" -name "PHASE" 2>/dev/null | grep -v '.gitkeep' | head -1 || true)

if [ -z "$PHASE_FILE" ] || [ ! -f "$PHASE_FILE" ]; then
  # No active feature — nothing to report
  exit 0
fi

PHASE=$(cat "$PHASE_FILE")
FEATURE_DIR=$(dirname "$PHASE_FILE")
FEATURE=$(basename "$FEATURE_DIR")

echo "=== ACTIVE FEATURE: $FEATURE ==="
echo "Phase: $PHASE"
echo ""

# Show current task (if in implement phase)
CURRENT_TASK_FILE="$FEATURE_DIR/CURRENT_TASK"
if [ -f "$CURRENT_TASK_FILE" ]; then
  CURRENT_TASK=$(cat "$CURRENT_TASK_FILE" | tr -d '[:space:]')
  echo "=== CURRENT TASK: $CURRENT_TASK ==="
  echo "Resume work on Task $CURRENT_TASK. Check dependencies in tasks.md before proceeding."
  echo ""
fi

# Show task status
TASKS_FILE="$FEATURE_DIR/tasks.md"
if [ -f "$TASKS_FILE" ]; then
  echo "=== TASK STATUS ==="
  cat "$TASKS_FILE"
  echo ""
fi

# Show git state — only repos with staged/modified files (not just untracked CLAUDE.md)
echo "=== GIT STATE ==="
ACTIVE_BRANCH=""
for repo_dir in "$PROJECT_DIR"/*/; do
  [ -d "$repo_dir/.git" ] || continue
  # Only show repos with modified or staged files (M, A, D, R, C prefixes)
  repo_changes=$(git -C "$repo_dir" status --short 2>/dev/null | grep -E '^( ?[MADRC]|[MADRC])' || echo "")
  # Also show untracked non-CLAUDE.md files
  repo_untracked=$(git -C "$repo_dir" status --short 2>/dev/null | grep '^??' | grep -v 'CLAUDE.md' || echo "")
  all_changes=$(printf '%s\n%s' "$repo_changes" "$repo_untracked" | sed '/^$/d')
  if [ -n "$all_changes" ]; then
    repo_name=$(basename "$repo_dir")
    repo_branch=$(git -C "$repo_dir" branch --show-current 2>/dev/null || echo "unknown")
    echo "Repo: $repo_name (branch: $repo_branch)"
    echo "$all_changes"
    echo ""
    ACTIVE_BRANCH="$repo_branch"
  fi
done

echo ""

# Warn if relevant repo is on main with an active implement-phase feature
if [[ "$PHASE" == "implement" || "$PHASE" == "complete" ]]; then
  if [[ "$ACTIVE_BRANCH" == "main" || "$ACTIVE_BRANCH" == "master" ]]; then
    echo "WARNING: Active repo is on '$ACTIVE_BRANCH' but feature '$FEATURE' is in phase '$PHASE'."
    echo "Create a feature branch before making changes:"
    echo "  git checkout -b feat/$FEATURE"
    echo ""
  fi
fi

exit 0
