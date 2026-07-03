---
name: architecture
description: >
  Official Feature-Sliced Design (FSD) v2.1 skill for applying the methodology
  to frontend projects. Use when the task involves organizing project structure
  with FSD layers, deciding where code belongs, placing static assets (images,
  icons, fonts, PDFs), grouping closely related slices, defining public APIs
  and import boundaries, resolving cross-imports or evaluating the @x pattern,
  deciding whether to create or remove an entity, evaluating whether the
  entities layer is needed at all, deciding whether logic should remain local
  or be extracted, migrating from FSD v2.0 or a non-FSD codebase, integrating
  FSD with frameworks (Next.js App Router and Pages Router, Nuxt, Vite,
  Astro), or implementing common patterns such as authentication, API
  handling, Redux, and TanStack Query (React Query) within FSD.
---

# Feature-Sliced Design (FSD) v2.1

> **Source**: [fsd.how](https://fsd.how) | Strictness can be adjusted based on
> project scale and team context.

## Project-Specific Priority: Target Project Style

When migrating or rewriting `frontend-supvz`, the primary target is the mature
project-specific FSD style described in these instructions. Treat official FSD
v2.1 guidance as the baseline, but when it conflicts with the conventions
below, prefer these project conventions.

For this project family, target a mature six-layer FSD structure rather than a
minimal `app/` + `pages/` + `shared/` layout:

```text
app/       → layouts, providers, createBrowserRouter, guards, role routes
pages/     → role-based route slices, e.g. admin/main, any/orders
widgets/   → app shell blocks and large composite route widgets
features/  → reusable user interactions
entities/  → stable business domains with api/model/ui segments
shared/    → UI kit, infrastructure, constants, hooks, generic types
```

Use these project conventions as defaults:

- Pages may be grouped by role: `pages/admin/main`, `pages/merchant/shops`,
  `pages/any/orders`, `pages/admin-and-support/shops`.
- App routing lives in `app/router/` with `router.tsx`, `public-routes.tsx`,
  `protected-routes.tsx`, `guards/`, and `roles/*-routes.tsx`.
- Entities usually expose `api/`, `model/`, and sometimes `ui/` through a
  slice-level `index.ts`.
- Entity APIs use individual request files plus an API barrel and, when
  TanStack Query is used, a `*.queries.ts` factory exported as `queries`.
- Slice public APIs may export API namespaces, e.g.
  `export * as orderApi from "./api"`.
- Shared may contain `ui/`, `lib/`, `constants/`, `hooks/`, `types/`, `mocks/`,
  and `tests/`, as long as it stays free of business logic.
- File names are kebab-case for UI/API files and may use domain-prefixed
  technical suffixes such as `order.types.ts`, `order.constants.ts`,
  `order.context.tsx`, `unload.store.ts`, and `order.queries.ts`.

Known legacy exceptions in existing code (for example direct imports from
`@/pages/.../ui/page`) should not be copied. New code should prefer slice
public APIs.

---

## 1. Core Philosophy & Layer Overview

FSD v2.1 core principle: **"Start simple, extract when needed."**

Place code in `pages/` first. Duplication across pages is acceptable and does
not automatically require extraction to a lower layer. Extract only when the
same code is currently being used in multiple places (not hypothetically),
the usages do not always change together, and the boundary has a focused
responsibility.

**Not all layers are required.** Most projects can start with only `shared/`,
`pages/`, and `app/`. Add `widgets/`, `features/`, `entities/` only when they
provide clear value. Do not create empty layer folders "just in case."

**Migration exception:** because the target architecture is mature FSD, stable
existing domains may be extracted during migration even before every reuse
relationship is fully proven. Prefer clear domain boundaries over a temporary
minimal structure.

FSD uses 6 standardized layers, listed here from highest to lowest:

```text
app/       → App initialization, providers, routing
pages/     → Route-level composition, owns its own logic
widgets/   → Large composite UI blocks reused across multiple pages
features/  → Reusable user interactions (only when used in 2+ places)
entities/  → Reusable business domain models (only when used in 2+ places)
shared/    → Infrastructure with no business logic (UI kit, utils, API client)
```

**Import rule**: A module may only import from layers strictly below it.
Cross-imports between slices on the same layer are forbidden.

```typescript
// ✅ Allowed
import { Button } from "@/shared/ui/Button"; // features → shared
import { useUser } from "@/entities/user"; // pages → entities

// ❌ Violation
import { loginUser } from "@/features/auth"; // entities → features
import { likePost } from "@/features/like-post"; // features → features
```

**Note**: The `processes/` layer is **deprecated** in v2.1. For migration
details, read `references/migration-guide.md`.

---

## 2. Decision Framework

When writing new code, follow this tree:

**Step 1: Where is this code used?**

- Used in only one page → keep it in that `pages/` slice.
- Used in 2+ pages but duplication is manageable → keeping separate copies
  in each page is also valid.
- An entity or feature used in only one page → keep it in that page
  (Steiger: `insignificant-slice`).

**Step 2: Is it reusable infrastructure with no business logic?**

- UI components → `shared/ui/`
- Utility functions → `shared/lib/`
- API client setup → `shared/lib/axios/` or `shared/api/` depending on the
  existing project convention
- Route constants and app-wide constants → `shared/constants/`
- Generic hooks and generic types → `shared/hooks/`, `shared/types/`
- Auth/session domain for this project family → prefer `entities/session/`
  and `entities/user/`; keep only pure token-storage infrastructure in Shared
- Domain request functions → usually `entities/<domain>/api/`; keep only
  generic API client primitives in Shared

**Step 3: Is it a complete user action currently used in multiple places,
with stable boundaries?**

- Yes → `features/`
- Uncertain, single use, or speculative reuse → keep in the page.

**Step 4: Is it a business domain model currently used in multiple places,
with stable boundaries?**

- Yes → `entities/`
- For this migration, if the domain is already stable in the
  legacy codebase (for example employee, payment, salary, PVZ, approval,
  request, notification), creating an entity can be the right move even while
  converting usages incrementally.
- Uncertain, single use, or speculative reuse → keep in the page.

**Step 5: Is it app-wide configuration?**

- Global providers, router, guards, role routes, layout shell, theme → `app/`

**Golden Rule: When in doubt, keep it in `pages/`. Extract only when the
same code is actively used in multiple places and the boundary is clear.**

---

## 3. Quick Placement Table

| Scenario              | Single use                                  | Confirmed multi-use                   |
| --------------------- | ------------------------------------------- | ------------------------------------- |
| User profile form     | `pages/profile/ui/ProfileForm.tsx`          | `features/profile-form/`              |
| Product card          | `pages/products/ui/ProductCard.tsx`         | `entities/product/ui/ProductCard.tsx` |
| Product data fetching | `pages/product-detail/api/fetch-product.ts` | `entities/product/api/`               |
| Auth/session domain   | `entities/session/`                         | `entities/session/`                   |
| Auth login form       | `pages/login/ui/LoginForm.tsx`              | `features/auth/`                      |
| Generic CRUD helper   | `shared/api/` or `shared/lib/axios/`         | `shared/api/` or `shared/lib/axios/`  |
| Domain API operations | Owning page/feature `api/`                   | `entities/<domain>/api/`              |
| Generic Card layout   |                                             | `shared/ui/Card/`                     |
| Modal manager         |                                             | `shared/ui/modal-manager/`            |
| Modal content         | `pages/[page]/ui/SomeModal.tsx`             |                                       |
| Date formatting util  |                                             | `shared/lib/format-date.ts`           |

---

## 4. Architectural Rules (MUST)

These rules are the foundation of FSD. Violations weaken the architecture.
If you must break a rule, ensure it is an intentional design decision and
document the reason in code (a comment or ADR).

### 4-1. Import only from lower layers

`app → pages → widgets → features → entities → shared`.
Upward imports and cross-imports between slices on the same layer are
forbidden.

### 4-2. Public API: every slice exports through index.ts

External consumers may only import from a slice's `index.ts`. Direct imports
of internal files are forbidden.

```typescript
// ✅ Correct
import { LoginForm } from "@/features/auth";

// ❌ Violation: bypasses public API
import { LoginForm } from "@/features/auth/ui/LoginForm";
```

**Shared layer:** Shared has no slices. Define a separate public API per
segment (`shared/ui/index.ts`, `shared/api/index.ts`, etc.) rather than
one top-level `shared/index.ts`. This keeps imports from Shared
organized by intent.

**RSC / meta-framework exception:** Split entry points
(`index.client.ts`, `index.server.ts`) are permitted. Details and rules:
`references/framework-integration.md`.

### 4-3. No cross-imports between slices on the same layer

If two slices on the same layer need to share logic, follow the resolution
order in Section 7. Do not create direct imports.

### 4-4. Domain-based file naming (no desegmentation)

Name files after the business domain they represent, not their technical role.
Technical-role names like `types.ts`, `utils.ts`, `helpers.ts` mix unrelated
domains in a single file and reduce cohesion.

```text
// ❌ Technical-role naming
model/types.ts          ← Which types? User? Order? Mixed?
model/utils.ts

// ✅ Domain-based naming
model/user.ts           ← User types + related logic
model/order.ts          ← Order types + related logic
model/order.types.ts    ← project style: domain-prefixed type file
model/order.constants.ts
model/order.context.tsx
api/order.queries.ts
api/fetch-profile.ts    ← Clear purpose
```

Domain-prefixed technical suffixes are allowed and preferred in this project:
`*.types.ts`, `*.constants.ts`,
`*.context.tsx`, `*.context.provider.tsx`, `*.store.ts`, `*.queries.ts`.
Avoid only vague suffix-only files like `types.ts`, `constants.ts`,
`utils.ts`, or `helpers.ts`.

### 4-5. No business logic in shared/

Shared contains only infrastructure: UI kit, utilities, API client setup,
route constants, assets. Business calculations, domain rules, and workflows
belong in `entities/` or higher layers.

```typescript
// ❌ Business logic in shared
// shared/lib/userHelpers.ts
export const calculateUserReputation = (user) => { ... };

// ✅ Move to the owning domain
// entities/user/lib/reputation.ts
export const calculateUserReputation = (user) => { ... };
```

---

## 5. Recommendations (SHOULD)

### 5-1. Pages First: place code where it is used

Place code in `pages/` first. Extract to lower layers only when truly needed.
Extraction is a design decision that affects the whole project, so the
threshold should be high.

For this migration, apply this as a design heuristic, not as a blocker.
Because the target is a mature FSD architecture, migrating stable legacy domains
directly into `entities/` and reusable interactions into `features/` is
acceptable when it improves the final structure.

**What stays in pages:**

- Large UI blocks used only in one page
- Page-specific forms, validation, data fetching, state management
- Page-specific business logic and API integrations
- Code that looks reusable but is simpler to keep local

**Evolution pattern:** Start with everything in `pages/profile/`. When the
same user data is being consumed by another page (not hypothetically),
extract the shared model to `entities/user/`. Keep page-specific API calls
and UI in the page.

### 5-2. Be conservative with entities

The entities layer is highly accessible (almost every other layer can import
from it), so changes propagate widely.

1. **Start without entities in small projects.** `shared/` + `pages/` + `app/`
  is valid FSD. Thin-client apps rarely need entities. For this migration,
  the target is already a mature FSD architecture, so stable existing domains
  may start in `entities/`.
2. **Do not split slices prematurely.** Keep code in pages. Extract to
   entities only when the same code is currently used by multiple
   consumers and the boundary is stable.
3. **Business logic does not automatically require an entity.** Keeping types
   in `shared/api` and logic in the current slice's `model/` segment may
   be sufficient.

For detailed guidance on keeping the entities layer clean (when to skip
it entirely, how to isolate business contexts, why CRUD belongs in
`shared/api`), see `references/excessive-entities.md`.

In this project style, entities also own domain API functions and TanStack
Query factories when the domain is reused broadly. Do not move these domain
APIs to Shared merely because they are CRUD-like.

### 5-3. Start with minimal layers

```text
// ✅ Valid minimal FSD project
src/
  app/         ← Providers, routing
  pages/       ← All page-level code
  shared/      ← UI kit, utils, API client

// Add layers only when an actual use case requires them:
// + widgets/   ← UI blocks currently reused across multiple pages
// + features/  ← User interactions currently reused across multiple pages
// + entities/  ← Domain models currently reused across pages or features
```

### 5-4. Validate with the Steiger linter

[Steiger](https://github.com/feature-sliced/steiger) is the official FSD
linter. Key rules:

- **`insignificant-slice`**: Suggests merging an entity/feature into its page
  if only one page uses it.
- **`excessive-slicing`**: Suggests merging or grouping when a layer has too
  many slices.

```bash
npm install -D @feature-sliced/steiger
npx steiger src
```

---

## 6. Anti-patterns (AVOID)

- **Do not create entities prematurely.** Data structures used in only one
  place belong in that place unless they are stable legacy domains being
  migrated to the target structure.
- **Do not create a `user` entity just for auth data.** In this project family,
  auth/session belongs primarily in `entities/session`; reusable user and role
  domain types belong in `entities/user`.
- **Do not abuse `@x`.** It is a necessary compromise, not a recommended
  pattern. The notation is for the entities layer only, and only when
  boundary merge is genuinely impossible. Features and widgets handle
  cross-imports through strategies A–D (see Section 7).
- **Do not extract single-use code.** A feature or entity used by only one
  page should stay in that page.
- **Do not use technical-role file names.** Use domain-based names
  (see Rule 4-4). Domain-prefixed suffixes like `order.types.ts` are allowed;
  suffix-only files like `types.ts` are not.
- **Do not create god slices.** Slices with excessively broad responsibilities
  should be split into focused slices (e.g., split `user-management/` into
  `auth/`, `profile-edit/`, `password-reset/`).
- **Do not create a top-level `assets/` segment.** Place static assets next
  to the code that uses them. See `references/asset-handling.md`.

---

## 7. Cross-Import Resolution

Cross-imports are a code smell, not an absolute prohibition. The right
strategy depends on the layer and the situation.

### Entities layer: prefer boundary merge, @x is last resort

Cross-imports in `entities` are usually caused by splitting entities too
granularly. Before reaching for `@x`, consider whether the boundaries
should be merged.

`@x` is a **necessary compromise, not a recommended approach**. Use it only
when boundaries genuinely cannot be merged, and document why. Overuse locks
entity boundaries together and increases refactoring cost.

### Features and widgets: four strategies (A, B, C, D)

In `features` and `widgets`, choose based on context:

- **Strategy A: Slice merge.** Two slices always change together → merge.
- **Strategy B: Push to entities.** Shared domain logic → move to
  `entities/`, keep UI in features/widgets.
- **Strategy C: Compose from upper layer (IoC).** The parent (pages or app)
  imports both slices and connects them via render props, slots, or DI.
- **Strategy D: Public API access.** When reuse is genuinely unavoidable,
  allow it only through the slice's `index.ts`. Never reach into `model/`,
  `store/`, or internal files.

The `@x` notation is for the entities layer only. Features and widgets use
strategies A–D above.

### Strictness depends on project context

Cross-imports are dependencies that are generally best avoided, but
sometimes used intentionally. Strictness varies by project context:

- **Early-stage products** with heavy experimentation: allowing some
  cross-imports may be a pragmatic speed trade-off.
- **Long-lived or regulated systems** (fintech, large-scale services):
  stricter boundaries pay off in maintainability and stability.

If a cross-import is introduced, treat it as a deliberate choice and
document the reasoning in code (a comment explaining why other strategies
do not apply).

For detailed code examples of each strategy, read
`references/cross-import-patterns.md`.

---

## 8. Segments & Structure Rules

### Standard segments

Segments group code within a slice by technical purpose:

- **`ui/`**: UI components, styles, display-related code
- **`model/`**: Data models, state stores, business logic, validation
- **`api/`**: Backend integration, request functions, API-specific types
- **`lib/`**: Internal utility functions for this slice
- **`config/`**: Configuration, feature flags

Project-specific Shared segments are also allowed:
`constants/`, `hooks/`, `types/`, `mocks/`, and `tests/`.

### Layer structure rules

- **App and Shared**: No slices, organized directly by segments. Segments
  within these layers may import from each other.
- **Pages, Widgets, Features, Entities**: Slices first, then segments inside
  each slice.
- **Slice groups (optional)**: A group folder may contain related slices on
  the same layer for navigation purposes only. The group has no segments and
  no public API. See `references/layer-structure.md` for details.

### File naming within segments

Always use domain-based names that describe what the code is about:

```text
model/user.ts            ← User types + logic + store
model/order.ts           ← Order types + logic + store
model/order.types.ts     ← Domain-prefixed types, project style
model/order.constants.ts ← Domain-prefixed constants
model/order.context.tsx  ← Domain-prefixed context
api/order.queries.ts     ← Domain-prefixed TanStack Query factory
api/fetch-profile.ts     ← Profile fetching
api/update-settings.ts   ← Settings update
```

If a segment has only one domain concern, the filename may match the slice
name (e.g., `features/auth/model/auth.ts`).

---

## 9. Shared Layer Guide

Shared contains infrastructure with **no business logic**. It is organized by
segments only (no slices). Segments within shared may import from each other.

**Allowed in shared:**

- `ui/`: UI kit (Button, Input, Modal, Card)
- `lib/`: Utilities (formatDate, debounce, classnames)
- `lib/axios/` or `api/`: API client primitives and HTTP infrastructure
- `constants/`: Route constants, sidebar metadata, app-wide values
- `hooks/`: Generic reusable hooks
- `types/`: Generic response, pagination, React utility, and shared DTO types
- `mocks/`: Reusable test/mock data
- `tests/`: Shared test utilities
- `config/`: Environment variables, app settings when needed
- `assets/`: Branding assets shared across the app (use sparingly; see
  `references/asset-handling.md`)

Shared **may** contain application-aware code (route constants, API endpoints,
branding assets, common types). It must **never** contain business logic,
feature-specific code, or entity-specific code.

---

## 10. Quick Reference

- **Import direction**: `app → pages → widgets → features → entities → shared`
- **Minimal FSD**: `app/` + `pages/` + `shared/`
- **Target structure**: mature project FSD with all six layers
  when the migrated code has stable domains and reusable app-shell blocks.
- **Create entities when**: the same business domain model is currently
  used across multiple pages, features, or widgets, with stable
  boundaries.
- **Create features when**: the same user interaction is currently used
  across multiple pages or widgets, with stable boundaries.
- **Breaking rules**: Only as an intentional design choice. Document the
  reason in code (comment or ADR).
- **Cross-import resolution (entities)**: Merge boundaries first; `@x` is a
  necessary compromise, not recommended.
- **Cross-import resolution (features/widgets)**: Strategy A (merge), B
  (push to entities), C (compose from upper layer), or D (Public API).
  The `@x` notation is for entities only.
- **File naming**: Domain-based (`user.ts`, `order.ts`) or domain-prefixed
  (`order.types.ts`, `order.queries.ts`). Never suffix-only technical-role
  files (`types.ts`, `utils.ts`).
- **Asset placement**: Place next to the code that uses them; reuse goes to
  `shared/ui/`; global stylesheets and fonts go to `app/`.
- **Slice groups**: Optional navigation aid for large layers; group folder
  has no segments and no public API.
- **Processes layer**: Deprecated. See `references/migration-guide.md`.

---

## 11. Conditional References

Read the following reference files **only** when the specific situation applies.
Do **not** preload all references.

- **When creating, reviewing, or reorganizing folder and file structure** for
  FSD layers and slices, including grouping closely related slices into a
  parent folder for navigation (e.g., "set up project structure", "where does
  this folder go", "how do I group these payment entities"):
  → Read `references/layer-structure.md`

- **When resolving cross-import issues** between slices on the same layer,
  evaluating the `@x` pattern, choosing between Strategy A/B/C/D for
  features and widgets, or deciding whether boundaries should be merged:
  → Read `references/cross-import-patterns.md`

- **When deciding whether to create or remove an entity**, dealing with too
  many entities, evaluating whether to skip the entities layer entirely,
  placing CRUD operations, deciding where authentication data belongs, or
  isolating business contexts to avoid `@x` chains:
  → Read `references/excessive-entities.md`

- **When deciding where to place static assets** (images, icons, fonts,
  PDFs, stylesheets) for a single slice, for sharing across slices, or
  globally:
  → Read `references/asset-handling.md`

- **When migrating** from FSD v2.0 to v2.1, converting a non-FSD codebase to
  FSD, or deprecating the processes layer:
  → Read `references/migration-guide.md`

- **When integrating FSD with a specific framework** (Next.js with App Router
  or Pages Router, Nuxt, Vite, CRA, Astro) for wiring routes to FSD pages,
  placing middleware/instrumentation files, structuring API route handlers,
  or configuring path aliases:
  → Read `references/framework-integration.md`

- **When implementing concrete code patterns** for authentication, API request
  handling, type definitions, or state management (Redux, TanStack Query /
  React Query, including query factories, infinite scroll, Suspense mode,
  and `useMutationState`) within FSD structure:
  → Read `references/practical-examples.md`
  Note: If you already loaded `layer-structure.md` in this conversation,
  avoid loading this file simultaneously. Address structure first, then load
  patterns in a follow-up step if needed.
