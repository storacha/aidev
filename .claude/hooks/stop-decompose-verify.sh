#!/bin/bash
# Stop Hook: Verify acceptance tests fail during decompose phase
#
# Only runs when:
# 1. Not already in a stop-hook loop
# 2. An active spec exists in decompose phase
# 3. Test files exist in the spec directory
#
# Exit codes:
#   0 = allow (with optional JSON block message on stdout)

# Resolve project root from hook location (.claude/hooks/ -> project root)
cd "$(cd "$(dirname "$0")/../.." && pwd)" || exit 0

INPUT=$(cat)

# Guard 1: Prevent infinite loop
if [ "$(echo "$INPUT" | jq -r '.stop_hook_active // false')" = "true" ]; then
  exit 0
fi

# Guard 2: Is there an active spec?
PHASE_FILE=$(find .specs/active -name PHASE 2>/dev/null | head -1)
[ -z "$PHASE_FILE" ] && exit 0

# Guard 3: Is it in decompose phase?
PHASE=$(cat "$PHASE_FILE")
[ "$PHASE" != "decompose" ] && exit 0

# Guard 4: Are there test files in the spec directory?
SPEC_DIR=$(dirname "$PHASE_FILE")
TEST_FILES=$(find "$SPEC_DIR" -maxdepth 3 \( -name "*.test.*" -o -name "*_test.go" -o -name "*.spec.*" -o -name "test_*" \) 2>/dev/null)
[ -z "$TEST_FILES" ] && exit 0

# All guards passed — we're in decompose phase with test files.
# Run the tests and verify they ALL fail.

# Determine test runner based on test file types
HAS_PY=$(echo "$TEST_FILES" | grep -c '\.py$' || true)
HAS_GO=$(echo "$TEST_FILES" | grep -c '_test\.go$' || true)
HAS_JS=$(echo "$TEST_FILES" | grep -c '\.\(test\|spec\)\.' || true)

EXIT=1  # default: tests fail (expected)

if [ "$HAS_PY" -gt 0 ]; then
  # Run Python tests
  for f in $(echo "$TEST_FILES" | grep '\.py$'); do
    python "$f" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
      EXIT=0
      break
    fi
  done
elif [ "$HAS_GO" -gt 0 ]; then
  go test ./... >/dev/null 2>&1
  EXIT=$?
elif [ "$HAS_JS" -gt 0 ]; then
  if [ -f package.json ]; then
    npm test >/dev/null 2>&1
    EXIT=$?
  fi
fi

if [ $EXIT -eq 0 ]; then
  # Tests passed — they should be FAILING in decompose phase
  echo "BLOCKED: One or more acceptance tests already pass. In decompose phase, all new tests must fail (RED)." >&2
  echo "Either the feature already exists or the test is vacuous. Investigate before moving to implement phase." >&2
  exit 2
fi

# Tests fail as expected — all good
exit 0
