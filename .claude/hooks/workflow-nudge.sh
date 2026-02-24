#!/bin/bash
# Workflow Nudge Hook (UserPromptSubmit)
# If no active spec exists, inject a reminder to use /dev.
# If an active spec exists, inject phase context to keep the AI on track.
#
# Output: JSON with additionalContext field

# Resolve project root from hook location (.claude/hooks/ -> project root)
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 0

ACTIVE=$(find .specs/active -name PHASE 2>/dev/null | head -1)
if [ -z "$ACTIVE" ]; then
  echo '{"additionalContext": "No active workflow detected. If this is a non-trivial feature request, suggest using /dev to structure the work."}'
else
  PHASE=$(cat "$ACTIVE")
  FEATURE=$(basename "$(dirname "$ACTIVE")")
  echo "{\"additionalContext\": \"Active workflow: $FEATURE (phase: $PHASE). Stay within phase constraints. Check .claude/rules/development-workflow.md for allowed actions in this phase.\"}"
fi
