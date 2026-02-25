#!/bin/bash
# Session Resume Hook (SessionStart)
# Re-inject active feature state into context at session boundaries.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

# Ensure workspace directories exist
mkdir -p "$PROJECT_DIR/.specs/active" "$PROJECT_DIR/.specs/done"

# Find active feature PHASE file
PHASE_FILE=$(find "$PROJECT_DIR/.specs/active" -name "PHASE" 2>/dev/null | grep -v '.gitkeep' | head -1 || true)

if [ -z "$PHASE_FILE" ] || [ ! -f "$PHASE_FILE" ]; then
  exit 0
fi

PHASE=$(cat "$PHASE_FILE")
FEATURE_DIR=$(dirname "$PHASE_FILE")
FEATURE=$(basename "$FEATURE_DIR")

echo "=== ACTIVE FEATURE: $FEATURE ==="
echo "Phase: $PHASE"
echo "Workflow: fullstack (use /fullstack to continue)"
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

# Show git state
echo "=== GIT STATE ==="
ACTIVE_BRANCH=""
# Check current directory git state
if [ -d "$PROJECT_DIR/.git" ]; then
  BRANCH=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || echo "unknown")
  CHANGES=$(git -C "$PROJECT_DIR" status --short 2>/dev/null | grep -E '^( ?[MADRC]|[MADRC])' || echo "")
  UNTRACKED=$(git -C "$PROJECT_DIR" status --short 2>/dev/null | grep '^??' | grep -v 'CLAUDE.md' || echo "")
  ALL=$(printf '%s\n%s' "$CHANGES" "$UNTRACKED" | sed '/^$/d')
  if [ -n "$ALL" ]; then
    echo "Branch: $BRANCH"
    echo "$ALL"
    echo ""
    ACTIVE_BRANCH="$BRANCH"
  fi
fi

# Also check sub-repos
for repo_dir in "$PROJECT_DIR"/*/; do
  [ -d "$repo_dir/.git" ] || continue
  repo_changes=$(git -C "$repo_dir" status --short 2>/dev/null | grep -E '^( ?[MADRC]|[MADRC])' || echo "")
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

# Warn if on main with active implement/complete feature
if [[ "$PHASE" == "implement" || "$PHASE" == "complete" ]]; then
  if [[ "$ACTIVE_BRANCH" == "main" || "$ACTIVE_BRANCH" == "master" ]]; then
    echo "WARNING: On '$ACTIVE_BRANCH' but feature '$FEATURE' is in phase '$PHASE'."
    echo "Create a feature branch: git checkout -b feat/$FEATURE"
    echo ""
  fi
fi

exit 0
