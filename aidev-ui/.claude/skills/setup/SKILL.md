---
name: setup
description: "Set up aidev-ui symlinks so Claude Code loads the fullstack UI process"
user_invocable: true
---

# Setup aidev-ui

Run the setup script from the project root to create symlinks:

```bash
./aidev-ui/setup.sh
```

This creates:
- `.claude` -> `aidev-ui/.claude` (hooks, rules, skills, settings)
- `CLAUDE.md` -> `aidev-ui/CLAUDE.md` (project instructions)
- `.specs` -> `aidev-ui/.specs` (workflow state + templates)

After setup, use `/fullstack` to begin a feature.

**Note:** Cannot coexist with `aidev/` — both create the same symlinks. Choose one per project.
