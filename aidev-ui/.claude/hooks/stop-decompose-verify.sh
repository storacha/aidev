#!/bin/bash
# Stop Hook: Verify acceptance tests fail during decompose phase
#
# Exit codes:
#   0 = allow
#   2 = block

# Resolve project root from hook location (.claude/hooks/ -> project root)
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 0

INPUT=$(cat)

# Guard 1: Prevent infinite loop
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active // false')" = "true" ]; then
  exit 0
fi

# Guard 2: Active spec?
PHASE_FILE=$(find .specs/active -name PHASE 2>/dev/null | head -1)
[ -z "$PHASE_FILE" ] && exit 0

# Guard 3: Decompose phase?
PHASE=$(cat "$PHASE_FILE")
[ "$PHASE" != "decompose" ] && exit 0

# Guard 4: Test files exist?
SPEC_DIR=$(dirname "$PHASE_FILE")
TEST_FILES=$(find "$SPEC_DIR" -maxdepth 3 \( -name "*.test.*" -o -name "*_test.go" -o -name "*.spec.*" -o -name "test_*" -o -name "*.stories.*" \) 2>/dev/null)
[ -z "$TEST_FILES" ] && exit 0

# Run tests and verify they ALL fail
HAS_JS=$(echo "$TEST_FILES" | grep -c '\.\(test\|spec\|stories\)\.' || true)

EXIT=1  # default: tests fail (expected)

if [ "$HAS_JS" -gt 0 ]; then
  if [ -f package.json ]; then
    npm test >/dev/null 2>&1
    EXIT=$?
  fi
fi

if [ $EXIT -eq 0 ]; then
  echo "BLOCKED: One or more acceptance tests already pass. In decompose phase, all new tests must fail (RED)." >&2
  echo "Either the feature already exists or the test is vacuous. Investigate before moving to implement phase." >&2
  exit 2
fi

exit 0
