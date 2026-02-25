# Fullstack UI Conventions

## File Naming
- Components: PascalCase (`UserProfile.tsx`, `NavBar.tsx`)
- Utilities/hooks: camelCase (`useAuth.ts`, `formatDate.ts`)
- Styles: kebab-case or co-located (`user-profile.css` or `UserProfile.module.css`)
- Tests: `ComponentName.test.tsx` or `ComponentName.spec.tsx`
- Stories: `ComponentName.stories.tsx`
- Design tokens: `tokens.json` or `design-tokens/*.json`

## Component Structure
```
ComponentName/
├── ComponentName.tsx
├── ComponentName.test.tsx
├── ComponentName.stories.tsx
└── index.ts
```

## Imports
- Prefer absolute imports (`@/components/...`, `@/lib/...`)
- Group order: React/framework -> external packages -> internal modules -> relative imports
- Use barrel exports for component directories

## Styling
- Tailwind CSS as primary styling approach
- Design tokens via CSS custom properties (`var(--color-primary)`)
- No inline `style={}` except for truly dynamic values
- Responsive: mobile-first (`sm:` -> `md:` -> `lg:` -> `xl:`)
- No hardcoded colors, spacing, or typography — always use tokens

## TypeScript
- Strict mode (`strict: true`)
- Props interfaces: `ComponentNameProps`
- Prefer `interface` for props, `type` for unions/utilities
- No `any` — use `unknown` and narrow

## Error Handling
- Error boundaries for component-level failures
- Structured error objects, not thrown exceptions in render paths
- Loading states: skeleton components preferred over spinners
- Always design the empty/zero-data state

## Accessibility
- Every interactive element: keyboard navigation + ARIA labels + contrast
- Use semantic HTML (`button`, `nav`, `main`, `article`) not `div` with roles
- Form inputs must have associated labels
- WCAG 2.1 AA minimum target
- Test with `getByRole()`, `getByLabelText()` not `getByTestId()`

## Testing
- Framework: Vitest or Jest + React Testing Library
- Test behavior, not implementation (no `querySelector`, no `instance()`)
- User event testing: `userEvent.click()`, `userEvent.type()`
- Visual: Storybook stories per component state
- A11y: axe-core assertions in test files
