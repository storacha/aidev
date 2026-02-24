#!/bin/bash
# Pre-commit Hook: Spec Exists Warning
# Warns when >5 files changed with no active spec.
# This is a WARNING only, not a blocking check.
# Install: copy to .git/hooks/pre-commit or .husky/pre-commit
#
# Exit codes:
#   0 = always (warning only, never blocks)

# Resolve project root from hook location (.claude/hooks/ -> project root)
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 0

FILE_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')
ACTIVE=$(find .specs/active -name PHASE 2>/dev/null | head -1)

if [ "$FILE_COUNT" -gt 5 ] && [ -z "$ACTIVE" ]; then
  echo "" >&2
  echo "WARNING: $FILE_COUNT files changed with no active spec." >&2
  echo "Consider using /dev to structure non-trivial work." >&2
  echo "This helps with traceability and prevents scope creep." >&2
  echo "" >&2
  # Warning only, not blocking — developer decides
fi

exit 0
