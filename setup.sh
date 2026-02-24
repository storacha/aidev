#!/bin/bash
# Setup aidev symlinks in the parent directory.
# Run this after cloning: ./aidev/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
AIDEV_NAME="$(basename "$SCRIPT_DIR")"

cd "$PARENT_DIR"

# Create symlinks (skip if they already exist and point to the right place)
for target in ".claude" "CLAUDE.md" ".specs"; do
  if [ -L "$target" ]; then
    echo "✓ $target symlink already exists"
  elif [ -e "$target" ]; then
    echo "⚠ $target already exists (not a symlink) — skipping"
  else
    ln -s "$AIDEV_NAME/$target" "$target"
    echo "✓ Created $target → $AIDEV_NAME/$target"
  fi
done

echo ""
echo "Done. Run 'claude' from $(pwd) to start."
