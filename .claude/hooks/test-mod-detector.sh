#!/bin/bash
# Test Modification Detector Hook (PreToolUse)
# Flags test file changes during the implement phase.
# Uses a bash pre-filter to avoid overhead on non-test writes.
# Only warns when a pre-existing acceptance test is being modified.
#
# Exit codes:
#   0 = allow (with optional warning on stderr)
#   2 = block (for strict mode — currently not enabled)

# Resolve project root from hook location (.claude/hooks/ -> project root)
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 0

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

# No file path = not a file write we care about
[ -z "$FILE_PATH" ] && exit 0

# Quick exit for non-implement phases
PHASE_FILE=$(find .specs/active -name PHASE 2>/dev/null | head -1)
[ -z "$PHASE_FILE" ] && exit 0
PHASE=$(cat "$PHASE_FILE")
[ "$PHASE" != "implement" ] && exit 0

# Quick exit for non-test files
IS_TEST=0
[[ "$FILE_PATH" =~ (test|spec|_test\.go) ]] && IS_TEST=1
[ $IS_TEST -eq 0 ] && exit 0

# This IS a test file modification during implement phase.
# Check if the test exists in the snapshot (pre-existing acceptance test being modified)
SPEC_DIR=$(dirname "$PHASE_FILE")
BASENAME=$(basename "$FILE_PATH")
if [ -f "$SPEC_DIR/tests-snapshot/$BASENAME" ]; then
  # Pre-existing acceptance test being modified — flag for developer review
  echo "WARNING: Modifying acceptance test '$BASENAME' during implementation." >&2
  echo "Acceptance tests define 'done' and should not be weakened during implementation." >&2
  echo "If the test is wrong, get developer approval first. If the code is wrong, fix the code." >&2
  # Exit 0 (allow) but with warning. For strict mode, change to exit 2 (block).
fi
exit 0
