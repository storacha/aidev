#!/bin/bash
# TDD Guard Hook (PreToolUse)
# During implement phase: block source file creation if no test snapshot exists.
#
# Exit codes:
#   0 = allow
#   2 = block

# Resolve project root from hook location (.claude/hooks/ -> project root)
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 0

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

[ -z "$FILE_PATH" ] && exit 0

# Find the active phase file
PHASE_FILE=$(find .specs/active -name PHASE 2>/dev/null | head -1)
[ -z "$PHASE_FILE" ] && exit 0

PHASE=$(cat "$PHASE_FILE")
[ "$PHASE" != "implement" ] && exit 0

# Only check source files, not tests/stories/configs
IS_SOURCE=0
[[ "$FILE_PATH" =~ \.(ts|tsx|js|jsx|go|py|css|scss)$ ]] && IS_SOURCE=1
[[ "$FILE_PATH" =~ (test|spec|_test\.go|\.stories\.) ]] && IS_SOURCE=0
[ $IS_SOURCE -eq 0 ] && exit 0

# Check that test snapshot exists
SPEC_DIR=$(dirname "$PHASE_FILE")
TESTS_DIR="$SPEC_DIR/tests-snapshot"
if [ ! -d "$TESTS_DIR" ] || [ -z "$(ls -A "$TESTS_DIR" 2>/dev/null)" ]; then
  echo "BLOCKED: No test snapshot found in $TESTS_DIR." >&2
  echo "Write and run acceptance tests first (Phase 4: Decompose + Test)." >&2
  echo "Use /fullstack to continue the workflow." >&2
  exit 2
fi
exit 0
