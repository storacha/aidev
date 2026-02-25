#!/bin/bash
# Setup aidev-ui symlinks in the parent directory.
# Run this after cloning: ./aidev-ui/setup.sh
#
# Creates symlinks so Claude Code loads the UI process:
#   .claude   → aidev-ui/.claude
#   CLAUDE.md → aidev-ui/CLAUDE.md
#   .specs    → aidev-ui/.specs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
AIDEV_NAME="$(basename "$SCRIPT_DIR")"

cd "$PARENT_DIR"

# Create symlinks (skip if they already exist and point to the right place)
for target in ".claude" "CLAUDE.md" ".specs"; do
  if [ -L "$target" ]; then
    CURRENT=$(readlink "$target")
    if [ "$CURRENT" = "$AIDEV_NAME/$target" ]; then
      echo "  $target symlink already correct"
    else
      echo "  WARNING: $target symlink points to '$CURRENT', not '$AIDEV_NAME/$target'"
      echo "  Remove it manually if you want to switch: rm $target"
    fi
  elif [ -e "$target" ]; then
    echo "  WARNING: $target already exists (not a symlink) — skipping"
    echo "  Remove or rename it to use aidev-ui: mv $target $target.bak"
  else
    ln -s "$AIDEV_NAME/$target" "$target"
    echo "  Created $target -> $AIDEV_NAME/$target"
  fi
done

echo ""
echo "Done. Run 'claude' from $(pwd) to start."
echo "Use /fullstack to begin a UI feature."
echo ""
echo "Figma agent setup (required for design generation):"
echo "  1. Create a Figma account for the agent (e.g. claude-dev@yourteam.com)"
echo "  2. Add as editor to your Figma team"
echo "  3. Generate a PAT from the agent's account settings"
echo "  4. export FIGMA_AGENT_PAT=fig_..."
