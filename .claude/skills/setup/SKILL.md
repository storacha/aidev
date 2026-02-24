---
name: setup
description: "Set up aidev symlinks in the parent directory so Claude Code works from the project root"
user_invocable: true
---

# Set up aidev for your project

Create the 3 symlinks in the parent directory that wire Claude Code to aidev's process files.

## Instructions

Run the setup script that ships with aidev:

```bash
./setup.sh
```

This creates 3 symlinks in the parent directory:
- `.claude → aidev/.claude` (hooks, rules, skills, settings)
- `CLAUDE.md → aidev/CLAUDE.md` (root instructions)
- `.specs → aidev/.specs` (workflow templates + state)

After the script runs successfully, tell the user:

> Setup complete. Now restart Claude Code from your project root:
> ```
> cd ..
> claude
> ```
> From there, clone any repos you need alongside aidev/:
> ```
> gh repo clone storacha/upload-service
> gh repo clone storacha/freeway
> ```
