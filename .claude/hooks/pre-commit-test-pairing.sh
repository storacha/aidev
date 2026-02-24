#!/bin/bash
# Pre-commit Hook: Test File Pairing
# Rejects commits where new source files have no corresponding test file.
# Install: copy to .git/hooks/pre-commit or .husky/pre-commit
#
# Exit codes:
#   0 = allow commit
#   1 = block commit

FAILED=0

for f in $(git diff --cached --name-only --diff-filter=A); do
  # Check JS/TS source files (not tests, not type declarations)
  if [[ "$f" =~ \.(ts|js)$ ]] && [[ ! "$f" =~ (test|spec|\.d\.ts) ]]; then
    test_file="${f/.ts/.test.ts}"
    alt_test="${f/.js/.test.js}"
    if ! git diff --cached --name-only | grep -qE "(${test_file}|${alt_test})"; then
      echo "ERROR: New source file $f has no corresponding test file." >&2
      echo "  Expected: $test_file or $alt_test" >&2
      FAILED=1
    fi
  fi

  # Check Go source files (not tests)
  if [[ "$f" =~ \.go$ ]] && [[ ! "$f" =~ _test\.go$ ]]; then
    test_file="${f/.go/_test.go}"
    if ! git diff --cached --name-only | grep -q "$test_file"; then
      echo "ERROR: New source file $f has no corresponding test file." >&2
      echo "  Expected: $test_file" >&2
      FAILED=1
    fi
  fi
done

if [ $FAILED -eq 1 ]; then
  echo "" >&2
  echo "Commit blocked: new source files must have corresponding test files." >&2
  echo "Use 'git commit --no-verify' to bypass for hotfixes." >&2
  exit 1
fi

exit 0
