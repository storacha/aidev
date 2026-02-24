# Enforcing Procedural Compliance for AI Coding Agents

## Research Report — February 2026

## Key Finding: 3-Layer Enforcement Architecture

| Layer | Mechanism | Reliability | When it fires |
|-------|-----------|-------------|---------------|
| **Layer 1: Rules** | `.claude/rules/*.md` | ~60-80% | Always loaded into context |
| **Layer 2: Hooks** | `.claude/settings.json` hooks | ~90%+ | Deterministic, fires on tool use |
| **Layer 3: CI/Pre-commit** | Hard gates | ~100% | Before commit/push |

### Layer 1: Rules (Guidelines)

Prompt-based instructions in `.claude/rules/` files. Always loaded, but compliance degrades:
- IFScale (Jaroslawicz 2025): Claude models drop to 42-53% accuracy at 500 instructions
- Primacy bias: earlier instructions get better adherence
- At extreme density, models shift to omitting entire instructions

Best practices:
- Keep rules short, imperative ("NEVER delete tests" not "Please try not to delete tests")
- Most critical rules first
- Modular files (one topic per file) beat monolithic CLAUDE.md
- Re-inject rules at phase transitions to refresh attention

### Layer 2: Hooks (Guardrails)

Claude Code hooks provide deterministic control:
- **PreToolUse**: Fires before any tool call, can return `deny` to block
- **PostToolUse**: Fires after tool execution for validation
- **Stop**: Fires when Claude finishes responding, can force continuation
- **UserPromptSubmit**: Fires before each user message is processed

From Anthropic docs:
> "If you tell Claude Code in your CLAUDE.md not to modify .env files, it will *probably* listen.
> If you set up a PreToolUse hook that blocks writes to .env files, it will *always* block them."

Key tools:
- **TDD Guard** (github.com/nizos/tdd-guard): PreToolUse hook blocking impl files until failing tests exist
- **Forced skill evaluation** (alexop.dev): UserPromptSubmit hook injecting mandatory skill check
- **Phase gate hook**: Reads filesystem state to gate allowed actions per phase

### Layer 3: CI/Pre-commit (Hard Gates)

Last line of defense:
- Pre-commit hooks rejecting commits without test files
- CI validation of test coverage
- Automated spec-to-test traceability checks

## What Does NOT Work

1. **Long rule files**: Instruction-following degrades past ~150 instructions
2. **Prompt-only constitutional constraints**: "Declarative prohibitions do not bind under optimization pressure" (arXiv:2506.02357)
3. **Mid-stream corrections**: 39% performance drop when instructions arrive across multiple turns vs upfront (Cline research)
4. **Self-correction loops**: Agents enter "death spirals of cascading errors" — revert and retry beats fix-in-place
5. **Oversized specs for small tasks**: Fowler critique of Kiro/spec-kit verbosity

## Context Isolation

Single-context TDD fails because the LLM "subconsciously designs tests around the implementation it's already planning" (alexop.dev).

Solution: separate subagents per phase:
- Test Writer Agent (RED): writes failing tests with zero implementation context
- Implementer Agent (GREEN): sees only the failing test, writes minimal code
- Raised TDD compliance from ~20% (skill-only) to ~84% (with hooks + subagent isolation)

## State Machine Enforcement

Use filesystem state to track workflow progress:
```
.specs/active/{feature}/
  PHASE           # "specify" | "design" | "decompose" | "implement"
  brief.md        # Phase 1 output
  design.md       # Phase 2 output (Tier 2+)
  tasks.md        # Phase 3 output
  tests-snapshot/ # Snapshot of test files at end of Phase 3
```

A PreToolUse hook reads PHASE file and denies file writes that don't match the current phase.

## Forced Skill Activation

From obra/superpowers framework:
- Skills trigger automatically based on context — "mandatory workflow steps that the agent cannot skip"
- UserPromptSubmit hook injects evaluation sequence before each response
- Agent must explicitly state which skills apply (YES/NO with reasoning)

## Sources

### Research Papers
- IFScale (Jaroslawicz 2025): arxiv.org/abs/2507.11538
- Constitutional SDD: arxiv.org/html/2602.02584
- Hierarchical Safety Principles: arxiv.org/html/2506.02357
- TDFlow: arxiv.org/abs/2510.23761

### Tools & Frameworks
- TDD Guard: github.com/nizos/tdd-guard
- Superpowers: github.com/obra/superpowers
- cc-sdd: github.com/gotalab/cc-sdd
- Stately Agent: github.com/statelyai/agent

### Practitioner Articles
- Anthropic Hooks Guide: code.claude.com/docs/en/hooks-guide
- alexop.dev: Forcing Claude Code to TDD
- Arguing with Algorithms: Technical Design Spec Pattern
- Cline: Worst Instructions for AI Coding Agents
- Addy Osmani: How to Write a Good Spec
- Martin Fowler: Understanding SDD Tools
- sedkodes.com: Building Competent AI SWE Agents Through Determinism
