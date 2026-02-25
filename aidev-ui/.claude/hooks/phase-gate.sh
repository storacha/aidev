#!/bin/bash
# Phase Gate Hook (PreToolUse)
# Reads current phase from .specs/active/*/PHASE
# Blocks file writes that don't match the current phase
#
# Phases: specify, visual-design, design, decompose, implement, complete
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
IS_STORY=0
IS_DESIGN_CONFIG=0

BASENAME=$(basename "$FILE_PATH")

# Classify file type
# Design config: JSON tokens, CSS custom properties, Tailwind config
if [[ "$BASENAME" =~ ^tokens\.json$ ]] || [[ "$FILE_PATH" =~ design-tokens/ ]] || [[ "$BASENAME" =~ \.tokens\.json$ ]]; then
  IS_DESIGN_CONFIG=1
elif [[ "$BASENAME" =~ tailwind\.config\. ]]; then
  IS_DESIGN_CONFIG=1
# Storybook stories
elif [[ "$BASENAME" =~ \.stories\.(ts|tsx|js|jsx)$ ]]; then
  IS_STORY=1
# Code files (ts/tsx/js/jsx/go/py/css/scss)
elif [[ "$FILE_PATH" =~ \.(ts|tsx|js|jsx|go|py|css|scss)$ ]]; then
  if [[ "$BASENAME" =~ (\.test\.|\.spec\.|_test\.go|__test__|test_) ]]; then
    IS_TEST=1
  else
    IS_SOURCE=1
  fi
fi

case "$PHASE" in
  specify)
    if [ $IS_SOURCE -eq 1 ] || [ $IS_TEST -eq 1 ] || [ $IS_STORY -eq 1 ] || [ $IS_DESIGN_CONFIG -eq 1 ]; then
      echo "BLOCKED: Phase is 'specify'. No source, test, story, or config files allowed yet." >&2
      echo "Complete the specify phase before writing any code. Use /fullstack to continue." >&2
      exit 2
    fi
    ;;
  visual-design)
    # Allow prototype files in prototypes/ directory
    if [[ "$FILE_PATH" =~ prototypes/ ]]; then
      exit 0
    fi
    if [ $IS_SOURCE -eq 1 ] || [ $IS_TEST -eq 1 ] || [ $IS_STORY -eq 1 ]; then
      echo "BLOCKED: Phase is 'visual-design'. Only design config files and prototypes/ are allowed." >&2
      echo "No production source, test, or story files yet. Use /fullstack to continue." >&2
      exit 2
    fi
    # IS_DESIGN_CONFIG is allowed
    ;;
  design)
    if [ $IS_SOURCE -eq 1 ] || [ $IS_TEST -eq 1 ] || [ $IS_STORY -eq 1 ] || [ $IS_DESIGN_CONFIG -eq 1 ]; then
      echo "BLOCKED: Phase is 'design'. Only markdown files allowed." >&2
      echo "Complete the design phase before writing code. Use /fullstack to continue." >&2
      exit 2
    fi
    ;;
  decompose)
    if [ $IS_SOURCE -eq 1 ]; then
      echo "BLOCKED: Phase is 'decompose'. Only test files and Storybook stories allowed, not source files." >&2
      echo "Write acceptance tests first. Source files are allowed in the 'implement' phase." >&2
      exit 2
    fi
    # IS_TEST and IS_STORY are allowed
    ;;
  implement)
    if [ $IS_TEST -eq 1 ] || [ $IS_STORY -eq 1 ]; then
      echo "BLOCKED: Phase is 'implement'. Acceptance tests and stories are frozen." >&2
      echo "If you believe the test is wrong, use /review to get an independent assessment." >&2
      exit 2
    fi
    ;;
esac
exit 0
