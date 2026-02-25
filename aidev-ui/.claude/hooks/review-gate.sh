#!/bin/bash
# Phase Transition Gate Hook (PreToolUse: Edit|Write)
# Block PHASE transitions unless prerequisites are met.
#
# Enforcement:
#   decompose → implement: requires tests-snapshot/ AND subagent-attestation.json
#   implement → complete:  requires reviews/final.json AND all tasks marked done
#
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty')

# Only care about PHASE file writes
[ -z "$FILE_PATH" ] && exit 0
[[ "$FILE_PATH" != */PHASE ]] && exit 0
echo "$FILE_PATH" | grep -q '\.specs/active/' || exit 0

# Determine the new phase value
NEW_PHASE=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' | tr -d '[:space:]')

[ -z "$NEW_PHASE" ] && exit 0

SPEC_DIR=$(dirname "$FILE_PATH")
FEATURE=$(basename "$SPEC_DIR")

case "$NEW_PHASE" in
  "implement")
    # Gate 1: Tests must exist in snapshot
    SNAPSHOT_DIR="$SPEC_DIR/tests-snapshot"
    if [ ! -d "$SNAPSHOT_DIR" ] || [ -z "$(ls -A "$SNAPSHOT_DIR" 2>/dev/null)" ]; then
      cat >&2 <<EOF
BLOCKED: Cannot transition to 'implement' without acceptance tests.

Write tests first and copy them to:
  $SNAPSHOT_DIR/
EOF
      exit 2
    fi

    # Gate 2: Tests must have been written by a subagent
    if [ ! -f "$SPEC_DIR/subagent-attestation.json" ]; then
      cat >&2 <<EOF
BLOCKED: Cannot transition to 'implement' without subagent attestation.

Acceptance tests must be written by a subagent (Task tool) to ensure
context isolation. The /fullstack workflow writes this attestation
after the subagent produces the tests.

Missing: $SPEC_DIR/subagent-attestation.json
EOF
      exit 2
    fi
    ;;

  "complete")
    # Gate 3: Code review must exist
    if [ ! -f "$SPEC_DIR/reviews/final.json" ]; then
      cat >&2 <<EOF
BLOCKED: Cannot transition to 'complete' without a code review.

Run the review first:
  /review --final $FEATURE

The review writes an artifact to:
  $SPEC_DIR/reviews/final.json
EOF
      exit 2
    fi

    # Gate 4: All tasks must be done
    TASKS_FILE="$SPEC_DIR/tasks.md"
    if [ -f "$TASKS_FILE" ]; then
      TOTAL=$(grep -cE '^## Task [0-9]+' "$TASKS_FILE" 2>/dev/null || echo "0")
      DONE=$(grep -cE '^## Task [0-9]+.*✓' "$TASKS_FILE" 2>/dev/null || echo "0")
      if [ "$TOTAL" -gt 0 ] && [ "$DONE" -lt "$TOTAL" ]; then
        cat >&2 <<EOF
BLOCKED: Cannot transition to 'complete' — not all tasks are marked done.

Tasks: $DONE/$TOTAL completed in $TASKS_FILE
Mark all tasks with ✓ before proceeding.
EOF
        exit 2
      fi
    fi
    ;;
esac

exit 0
