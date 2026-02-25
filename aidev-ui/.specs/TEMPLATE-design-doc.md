# Design: {Feature Name}

## Component Architecture

```
FeatureName/
├── FeatureContainer.tsx    # State management, data fetching
├── FeatureView.tsx         # Layout, passes props to children
├── SubComponentA.tsx       # Description
└── SubComponentB.tsx       # Description
```

### Component Inventory
| Component | New/Existing | Props Interface | Stories Needed |
|-----------|-------------|-----------------|----------------|
| {Name} | New | {key props} | default, variant1, error, loading |

## Design Token Requirements
| Token | Current Value | Source |
|-------|--------------|--------|
| `--color-{name}` | {value} | Existing / New |

## State Management
- Local state: {what}
- Context: {what}
- External store: {what}

## API Integration
| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| {path} | GET/POST | {shape} | {shape} |

## Data Flow
```
User Action → Component → Hook → API → State Update → Re-render
```

## Files to Change
| File | Change Type | Description |
|------|-------------|-------------|
| `path/to/file` | New/Modify | What changes |

## Test Strategy
- Functional: {approach, mocks needed}
- Visual: {Storybook stories, Chromatic snapshots}
- A11y: {axe-core, keyboard tests}

## Responsive Strategy
- Mobile: {layout approach}
- Tablet: {layout approach}
- Desktop: {layout approach}

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| {description} | {impact} | {mitigation} |

## Performance Considerations
- Bundle size impact: {estimate}
- Render performance: {concerns}
- Data loading: {strategy — SSR, streaming, lazy}
