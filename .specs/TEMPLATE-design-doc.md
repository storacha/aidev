# [Feature Name] — Design Document

> **Tier 3 features only.** For Tier 2, add a `## Design Notes` section to `brief.md` instead.

## Feature Brief Reference

- **Brief:** `.specs/active/{feature-slug}/brief.md`
- **Appetite:** [from brief]
- **Acceptance Criteria Count:** [N]

## Architecture

### Current State

[Describe the current architecture relevant to this feature. Which services, packages, data flows are involved.]

### Proposed Changes

[Describe the changes at an architectural level. What new components, interfaces, data flows are introduced.]

### Architecture Diagram

```
[Text-based diagram showing component relationships and data flow]
[Use ASCII art or simple box diagrams]
```

## Files to Change

| File | Change Type | Description |
|------|-------------|-------------|
| `path/to/file.ts` | Modify | [What changes and why] |
| `path/to/new-file.ts` | Create | [What this file does] |

## Interfaces

```typescript
// Key interfaces that will be created or modified
// Include type signatures for new public APIs
```

## Data Flow

[Step-by-step description of how data moves through the system after changes]

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Test Infrastructure

### Existing Patterns

[Describe the testing patterns already used in the affected repos. Reference specific test files as examples.]

### New Test Infrastructure Needed

- [Any new test helpers, fixtures, mocks, or test utilities required]
- [External service mocks or stubs]

### Mocking Strategy

[How will external dependencies be mocked? Which test doubles are needed?]

## Migration Strategy

### Backward Compatibility

[Will this change be backward compatible? If not, what breaks?]

### Rollout Plan

1. [Step 1: e.g., deploy new version with feature flag]
2. [Step 2: e.g., migrate data]
3. [Step 3: e.g., enable feature]

### Data Migration

[Any database schema changes, data backfills, or format migrations needed]

## Rollback Plan

[How to revert if something goes wrong. Be specific.]

1. [Step 1]
2. [Step 2]

## Performance Considerations

- [Expected impact on latency, throughput, storage]
- [Any new caching needs]
- [Load testing requirements]

## Security Considerations

- [Any new auth requirements]
- [Data exposure risks]
- [Input validation needs]

## Open Questions

- [ ] [Question that needs answering before or during implementation]
