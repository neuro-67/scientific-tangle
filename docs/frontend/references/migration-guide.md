# Migration Guide

How to migrate to FSD v2.1 from either FSD v2.0 or a custom (non-FSD)
architecture. This guide reflects the official `from-custom` step order:
**pages first**, then everything else.

For this project, the target is not only official FSD v2.1, but the concrete
mature project FSD style described in these instructions. Use the
project-specific section below when planning this rewrite.

## Part 1: FSD v2.0 → v2.1 (non-breaking)

The v2.1 update emphasizes **"pages first"**: most logic stays in pages,
reusable foundation in Shared. If reuse is needed across several pages,
move it to a layer below. The migration is non-breaking and simplifies
the codebase by relocating single-use code back to where it is consumed.

Another addition in v2.1 is the standardization of cross-imports between
entities with the `@x` notation. See `references/cross-import-patterns.md`.

### Step 1. Audit existing slices

Use Steiger to detect slices that are used in only one place:

```bash
npm install -D @feature-sliced/steiger
npx steiger src
```

Look for these rules:

- **`insignificant-slice`**: an entity or feature used by only one page.
  This rule will suggest merging that entity or feature into the page
  entirely.
- **`excessive-slicing`**: too many slices in a single layer.

For each flagged slice, decide:

- Reused in 2+ places → keep in features/entities.
- Used only in one page → mark for migration back into that page.

### Step 2. Move single-use code back to its consumer

Take single-use features and entities and inline them into the consuming
page (or widget if that is the single consumer):

```text
// Before (v2.0): feature used by only one page
features/user-profile-form/
  ui/ProfileForm.tsx
  model/profile-form.ts
  api/update-profile.ts
  index.ts
pages/profile/
  ui/ProfilePage.tsx       ← Thin wrapper, just composes

// After (v2.1): code lives in the page that owns it
pages/profile/
  ui/{ProfilePage,ProfileForm}.tsx
  model/profile.ts          ← Merged form logic
  api/update-profile.ts
  index.ts
```

For each moved slice:

1. Copy all files into the consuming page.
2. Update the page's `index.ts` to export what is needed externally.
3. Update all imports across the codebase to point to the new location.
4. Delete the now-empty feature/entity directory.
5. Run tests.

### Step 3. Keep genuinely reused code in place

Code confirmed to be used in 2+ places stays in features/entities. Do not
move it. The point of v2.1 is reducing premature extraction, not removing
reuse.

### Step 4. Deprecate the processes layer

The `processes` layer is deprecated. Migrate its code:

- **Multi-page workflows** (checkout, onboarding wizard): move
  orchestration logic to the page that initiates the workflow. If multiple
  pages share workflow state, create a feature for it.
- **Background processes** (polling, sync): move to `app/` if global, or
  to the relevant page/feature if scoped.

```text
// Before
processes/
  checkout/model/checkout-flow.ts
  sync/model/background-sync.ts

// After
features/checkout/model/checkout-flow.ts    ← Used in 2+ pages
app/sync/background-sync.ts                  ← Global concern
```

### Post-migration verification

1. Run `npx steiger src`. All `insignificant-slice` warnings should be gone.
2. Verify import directions. No upward or same-layer cross-imports.
3. Check that no empty layer directories remain.
4. Update documentation to reflect the new structure.

## Part 2: Custom architecture → FSD

This part follows the official `from-custom` migration order. The core
philosophy is **pages first**: start by dividing the code by pages, then
work outward.

### Before you start

The most important question to ask the team is: *do you really need it?*
Some projects are perfectly fine without FSD. Reasons to consider the
switch:

1. New team members struggle to reach a productive level.
2. Modifications to one part of the code **often** break unrelated parts.
3. Adding new functionality is difficult due to the volume of context to
   hold in mind.

**Avoid switching to FSD against the will of teammates**, even as a lead.
Convince the team that the benefits outweigh migration and learning costs.
Explain the migration plan to management; architectural changes are not
immediately observable to them.

If the decision is made, set up a path alias for `src/` first. This guide
uses `@` as an alias for `./src`.

### Step 1. Divide the code by pages

If `pages/` already exists, skip this step. Otherwise, create `pages/` and
move as much component code as possible from `routes/` (or equivalent) into
it. Aim for tiny route files that just re-export from page slices.

```text
// Route file (thin)
src/routes/products.[id].js
  export { ProductPage as default } from "@/pages/product"

// Page slice
src/pages/product/
  ui/ProductPage.jsx
  index.js                ← export { ProductPage } from "./ProductPage.jsx"
```

Pages may reference each other for now. Tackle that later. Focus on
establishing a prominent division by pages.

### Step 2. Separate everything else from pages

Create `src/shared/` and move everything that does **not** import from
`pages/` or `routes/` there. Create `src/app/` and move everything that
**does** import the pages or routes there, including the routes themselves.

The Shared layer has no slices, so segments may import from each other.

```text
src/
  app/
    routes/
      products.jsx
      products.[id].jsx
    App.jsx
    index.js
  pages/
    product/
      ui/ProductPage.jsx
      index.js
    catalog/
  shared/
    actions/, api/, components/, containers/, constants/,
    i18n/, modules/, helpers/, utils/, reducers/, selectors/, styles/
```

### Step 3. Tackle cross-imports between pages

Find all cases where one page imports from another. Resolve each in one of
two ways:

1. **Copy-paste** the imported code into the depending page to remove the
   dependency.
2. **Move to a Shared segment**:
   - UI kit code → `shared/ui/`
   - configuration constants → `shared/config/`
   - backend interaction → `shared/api/`

Copy-pasting is **not architecturally wrong**. Sometimes it is more correct
to duplicate than to abstract into a new reusable module, because the
shared parts of pages can drift apart over time. Still, the DRY principle
holds for business logic: avoid copy-pasting code that must stay in sync
across multiple places.

### Step 4. Unpack the Shared layer

The Shared layer can become bloated after Step 2. Find every object used in
only one page and move it to that page's slice. **This applies to actions,
reducers, and selectors too.** There is no benefit in grouping all actions
together, but there is benefit in colocating relevant actions close to
their usage.

```text
src/
  pages/
    product/
      actions/, reducers/, selectors/, ui/   ← moved from shared
      index.js
    catalog/
  shared/                                    ← only objects that are reused
    actions/, api/, components/, ...
```

### Step 5. Organize code by technical purpose (segments)

In FSD, division by technical purpose is done with **segments**. The common
ones are:

- **`ui`**: everything related to UI display (components, date formatters,
  styles).
- **`api`**: backend interactions (request functions, data types, mappers).
- **`model`**: the data model (schemas, interfaces, stores, business
  logic).
- **`lib`**: library code that other modules in the slice need.
- **`config`**: configuration files and feature flags.

Custom segments are allowed when needed. **Do not create segments that
group code by what it is**, like `components`, `actions`, `types`, or
`utils`. Group code by what it is **for**, not by what it is. This is the
desegmentation principle.

Reorganize each page to separate code by segments:

- The existing page UI files become the `ui` segment.
- Actions, reducers, and selectors become the `model` segment.
- Thunks and mutations become the `api` segment.

Reorganize the Shared layer too:

- `components/`, `containers/` → most of it becomes `shared/ui/`.
- `helpers/`, `utils/` → group by function (dates, type conversions, etc.)
  and move groups to `shared/lib/`.
- `constants/` → group by function and move to `shared/config/`.

## Optional steps

### Step 6. Form entities/features from Redux slices used on several pages

Reused Redux slices typically describe business concepts (products, users)
or user actions (comments, likes):

- Business entities → **Entities layer**, one entity per folder.
- User actions → **Features layer**.

Entities and features are meant to be independent. If your business domain
contains inherent connections between entities (a song belongs to an
artist), see the
[business entities cross-references guide](https://fsd.how/docs/guides/examples/types#business-entities-and-their-cross-references).

In small/minimal projects, API functions related to these slices can stay in
`shared/api`. For this project, prefer the project convention: stable domain
requests live in `entities/<domain>/api/` and are exposed via an API namespace
from the entity public API.

### Step 7. Refactor your modules

The `modules/` folder typically holds business logic, similar in nature to
the Features layer. Some modules describe large UI chunks (an app header)
which belong in the Widgets layer.

### Step 8. Form a clean UI foundation in `shared/ui`

`shared/ui` should contain UI elements with no encoded business logic.
Refactor components from `components/` and `containers/` to extract their
business logic to higher layers. If business logic is not used in many
places, copy-pasting back to consumers is an acceptable choice.

## Common pitfalls during migration

1. **Extracting too early.** Wait for real reuse, not anticipated reuse.
   The v2.1 philosophy is "pages first, extract later".
2. **Creating empty layers.** Do not create `features/`, `entities/`, or
   `widgets/` directories until there is content for them.
3. **Refactoring while migrating.** Separate relocation from refactoring.
   Move files first, improve them in separate commits.
4. **Ignoring import direction.** Enforce import rules from day one with
   ESLint or Steiger.
5. **Big-bang migration.** Migrate page by page, verifying each step. A
   hybrid structure (partly FSD, partly legacy) is acceptable during
   transition.
6. **Grouping by technical role.** `components/`, `actions/`, `utils/` as
   segment names defeat the purpose of FSD. Group by what code is for.

## Part 3: Project-specific mature FSD migration

Use this checklist when converting the current structure to the target
architecture. This is intentionally more concrete than the generic from-custom
guide.

### 1. Move app bootstrap into `src/app`

Target shape:

```text
src/app/
  index.tsx
  layouts/
    root-layout.tsx
    app-layout.tsx
  providers/
    index.tsx
    query-client-provider.tsx
    theme-provider.tsx
  router/
    router.tsx
    public-routes.tsx
    protected-routes.tsx
    route-error-boundary.tsx
    guards/
      auth-guard.tsx
      guest-guard.tsx
    roles/
      admin-routes.tsx
      employee-routes.tsx
      index.tsx
```

Move current `src/App.tsx`, `src/index.tsx`, `src/providers/*`, and route
composition into this structure. Prefer `createBrowserRouter` and role route
arrays.

### 2. Convert flat `src/page` to role-based `src/pages`

Current flat page files should become page slices:

```text
src/page/HomePage.tsx
  → src/pages/any/home/ui/page.tsx
  → src/pages/any/home/index.ts

src/page/EmployeesPage.tsx
  → src/pages/admin/employees/ui/page.tsx
  → src/pages/admin/employees/index.ts
```

Pick groups by route audience: `admin/`, `employee/`, `any/`, or combined
groups such as `admin-and-manager/` if the application needs them. Export with
clear aliases, e.g. `export { Page as AdminEmployeesPage } from "./ui/page"`.

Route files in `app/router/roles/` must import pages through `index.ts`, not
from `ui/page`.

### 3. Move flat `src/api/*Service.ts` into domain APIs

For stable domain services, create entity API segments:

```text
src/api/employeeService.ts
  → src/entities/employee/api/get-employees.ts
  → src/entities/employee/api/create-employee.ts
  → src/entities/employee/api/employee.queries.ts
  → src/entities/employee/api/index.ts

src/api/paymentRecordService.ts
  → src/entities/payment/api/*
```

Entity API barrels should export request functions and `queries`; entity
public APIs should export namespace APIs:

```typescript
export * as employeeApi from "./api";
```

Keep only HTTP client setup, interceptors, and generic infrastructure in
`shared/lib/axios/` or `shared/api/`.

### 4. Move `src/types` into model or shared types

Use these rules:

- Domain types → `entities/<domain>/model/<domain>.types.ts`
- Page-only types → `pages/<role>/<page>/model/<page>.types.ts`
- Feature-only types → `features/<feature>/model/<feature>.types.ts`
- Generic API wrappers, pagination, React utility types → `shared/types/`

Avoid suffix-only files like `types.ts`; use domain-prefixed files such as
`employee.types.ts`, `salary.types.ts`, and `api.types.ts`.

### 5. Split `src/components` by ownership

Move components based on responsibility:

- Generic primitives and reusable UI kit → `shared/ui/`
- Domain display components → `entities/<domain>/ui/`
- Reusable user actions/forms → `features/<feature>/ui/`
- App shell or large composed blocks → `widgets/<widget>/ui/`
- Single-page sections/forms/modals → `pages/<role>/<page>/ui/`

Prefer kebab-case file names (`employee-card.tsx`) and PascalCase exports
(`EmployeeCard`).

### 6. Distribute global hooks

Move `src/hook/*` by ownership:

- Generic hook → `shared/hooks/`
- Domain hook → `entities/<domain>/model/` or `entities/<domain>/lib/`
- Feature-specific hook → `features/<feature>/model/`
- Page-specific hook → `pages/<role>/<page>/model/`

Do not keep a global `hook/` folder after migration.

### 7. Model auth/session using the project convention

Prefer:

```text
entities/session/       ← session API, session context, current session query
entities/user/          ← reusable user/role/permission domain types
app/router/guards/      ← auth and guest route guards
```

Only pure token storage or Axios interceptor infrastructure should remain in
Shared.

### 8. Use public APIs consistently

Every `pages`, `widgets`, `features`, and `entities` slice needs `index.ts`.
Consumers import from the slice root:

```typescript
import { EmployeeCard, employeeApi } from "@/entities/employee";
import { ChoosePvz } from "@/features/choose-pvz";
```

Treat direct imports from `@/pages/.../ui/page` or `@/entities/.../model/...`
as legacy exceptions, not target style.

### 9. Migrate incrementally

Move one route/domain at a time:

1. Create the target FSD slice.
2. Move files without large behavior changes.
3. Add or update `index.ts` public API.
4. Update imports.
5. Run TypeScript/tests/build.
6. Delete the old legacy folder only after imports are gone.

Temporary hybrid structure is acceptable, but new code should use the target
project conventions immediately.

## Migrating from FSD v1 to v2

This guide does not cover v1 → v2. See the official
[v1 to v2 migration guide](https://fsd.how/docs/guides/migration/from-v1).
The v1 → v2 transition introduced the entities and processes layers
(processes was later deprecated in v2.1).
