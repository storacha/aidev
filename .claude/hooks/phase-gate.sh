#!/bin/bash
# Phase Gate Hook (PreToolUse)
# Reads current phase from .specs/active/*/PHASE
# Blocks file writes that don't match the current phase
#
# Exit codes:
#   0 = allow
#   2 = block (Claude Code convention)

# Resolve project root from hook location (.claude/hooks/ -> project root)
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 0

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

# No file path = not a file write we care about
[ -z "$FILE_PATH" ] && exit 0

# Find active spec phase (if any)
# NOTE: Only one active spec at a time. Multiple concurrent specs not supported.
PHASE_FILES=()
while IFS= read -r f; do
  PHASE_FILES+=("$f")
done < <(find .specs/active -name PHASE 2>/dev/null)

if [ ${#PHASE_FILES[@]} -eq 0 ]; then
  exit 0  # No active workflow — no restrictions
fi
if [ ${#PHASE_FILES[@]} -gt 1 ]; then
  echo "BLOCKED: Multiple active specs found. Complete or archive one first." >&2
  exit 2
fi
PHASE_FILE="${PHASE_FILES[0]}"
PHASE=$(cat "$PHASE_FILE")

IS_TEST=0
IS_SOURCE=0

# Only classify code files (ts/js/go/py) — markdown and other files are always allowed
if [[ "$FILE_PATH" =~ \.(ts|js|go|py)$ ]]; then
  BASENAME=$(basename "$FILE_PATH")
  if [[ "$BASENAME" =~ (\.test\.|\.spec\.|_test\.go|__test__|test_) ]]; then
    IS_TEST=1
  else
    IS_SOURCE=1
  fi
fi

case "$PHASE" in
  specify|design)
    if [ $IS_SOURCE -eq 1 ] || [ $IS_TEST -eq 1 ]; then
      echo "BLOCKED: Phase is '$PHASE'. No source or test files allowed yet." >&2
      echo "Complete the current phase before writing code. Use /dev to continue the workflow." >&2
      exit 2
    fi
    ;;
  decompose)
    if [ $IS_SOURCE -eq 1 ]; then
      echo "BLOCKED: Phase is 'decompose'. Only test files allowed, not source files." >&2
      echo "Write acceptance tests first. Source files are allowed in the 'implement' phase." >&2
      exit 2
    fi
    ;;
  implement)
    if [ $IS_TEST -eq 1 ]; then
      echo "BLOCKED: Phase is 'implement'. Acceptance tests are frozen." >&2
      echo "If you believe the test is wrong, use /review to get an independent assessment." >&2
      echo "See 'Test Dispute Resolution' in .claude/rules/development-workflow.md." >&2
      exit 2
    fi
    ;;
esac
exit 0
