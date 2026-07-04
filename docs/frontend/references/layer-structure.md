# Layer Structure Reference

Detailed folder structures, code examples, and naming conventions for each
FSD layer. Use this reference when creating, reviewing, or reorganizing
project structure.

For this project, prefer the concrete conventions below over generic examples
when they differ. The target is a mature React/Vite FSD application with
role-based pages, entity API namespaces, and app-level router composition.

---

## App Layer

App-wide initialization: providers, routing, global styles, entry point.
Organized by segments only, no slices.

The methodology does not formally standardize App segment names. The
common convention list (`ui`, `api`, `model`, `lib`, `config`) applies to
all layers but is rarely a good fit here. In practice, projects use names
that describe purpose: `routes`, `store`, `styles`, `providers`,
`entrypoint`, etc. Choose names that match your stack (for example,
`providers` for React/Vue provider components that wrap Redux,
QueryClient, or theme contexts):

```text
app/
  layouts/         ← root-layout.tsx, app-layout.tsx
  providers/       ← query-client-provider.tsx, composed Providers
  router/          ← router.tsx, public/protected routes, guards, role routes
    guards/        ← auth-guard.tsx, guest-guard.tsx
    roles/         ← admin-routes.tsx, merchant-routes.tsx, trader-routes.tsx
  styles/          ← Global CSS, reset, theme variables if not in app/index.css
  index.tsx        ← Application entry point
```

A smaller project may collapse some of these into single files:

```text
app/
  router.tsx       ← Route configuration
  store.ts         ← Store configuration
  styles/
    global.css
  providers.tsx    ← All providers in one file
  index.tsx        ← Entry point
```

```typescript
// app/router/router.tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { RootLayout } from "../layouts/root-layout";
import { protectedRoutes } from "./protected-routes";
import { publicRoutes } from "./public-routes";

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [...publicRoutes, ...protectedRoutes],
  },
]);

export const AppRouterProvider = () => <RouterProvider router={router} />;
```

**Belongs in app:** Global providers (Redux store, QueryClient, theme),
routing setup, global styles, error boundaries, analytics initialization.

**Does not belong:** Feature-specific code, business logic, page-level UI.

---

## Pages Layer

Route-level composition. In v2.1, pages **own substantial logic**: they are
not thin wrappers. In early project stages, most code lives here.

```text
pages/
  home/
    ui/
      HomePage.tsx
      HeroSection.tsx
      FeaturesGrid.tsx
    model/
      home-data.ts          ← Page-specific state + logic
    api/
      fetch-home-data.ts    ← Page-specific API calls
    index.ts
  profile/
    ui/
      ProfilePage.tsx
      ProfileForm.tsx
      ProfileStats.tsx
    model/
      profile.ts            ← Profile state + validation logic
    api/
      update-profile.ts
      fetch-profile.ts
    index.ts
```

### Role-based pages

Prefer a role/group layout when routes differ by user role. The first folder
can be a role or route audience, and the second folder is the route slice:

```text
pages/
  admin/
    main/
      ui/page.tsx
      index.ts          ← export { MainPage as AdminMainPage } from "./ui/page"
    employees/
      ui/page.tsx
      index.ts
  merchant/
    main/
    settings/
  any/
    notifications/
    orders/
  admin-and-support/
    approvals/
    payments/
```

Role route files in `app/router/roles/` import pages through their public API:

```typescript
import { AdminMainPage } from "@/pages/admin/main";
import { OrdersPage } from "@/pages/any/orders";

export const adminRoutes = [
  { path: "/", element: <AdminMainPage /> },
  { path: "/orders", element: <OrdersPage /> },
];
```

Avoid copying legacy deep imports such as `@/pages/.../ui/page`; route files
should import from the page slice `index.ts`.

**Belongs in pages:** Page-specific UI, forms, validation, data fetching,
state management, business logic, API integrations. Even code that looks
reusable stays here if it is simpler to keep local.

**Does not belong:** Code that is currently being reused across multiple
pages with stable boundaries (extract to a lower layer when reuse is
confirmed, not anticipated).

### Page Layout Patterns

A typical page composes widgets, features, and entities from lower layers,
plus its own local UI components:

```typescript
// pages/product-detail/ui/ProductDetailPage.tsx
import { Header } from '@/widgets/header';
import { AddToCart } from '@/features/add-to-cart';
import { Product } from '@/entities/product';

export const ProductDetailPage = ({ productId }) => {
  const product = useProductDetail(productId); // local hook in this page

  return (
    <>
      <Header />
      <Product.Card data={product} />
      <AddToCart productId={productId} />
      <RelatedProducts products={product.related} /> {/* local component */}
    </>
  );
};
```

For pages that only need shared + page-local code (no extracted layers):

```typescript
// pages/about/ui/AboutPage.tsx
import { Card } from '@/shared/ui/Card';
import { TeamSection } from './TeamSection';  // local to this page
import { MissionStatement } from './MissionStatement';

export const AboutPage = () => (
  <main>
    <MissionStatement />
    <Card><TeamSection /></Card>
  </main>
);
```

---

## Widgets Layer

Composite UI blocks with their own logic, **reused across multiple pages**.
Add this layer only when UI blocks actually appear in 2+ pages and sharing
provides clear value.

```text
widgets/
  header/
    ui/
      Header.tsx
      Navigation.tsx
      UserMenu.tsx
    model/
      header.ts              ← Widget state
    api/
      fetch-notifications.ts
    index.ts
  sidebar/
    ui/
      Sidebar.tsx
    model/
      sidebar.ts
    index.ts
```

**Belongs in widgets:** Navigation bars, sidebars, dashboards, footers,
complex card layouts that combine data from multiple entities/features.

In this project style, app shell blocks such as `app-sidebar` and `app-navbar`
are widgets, and large route-level composite modules can also be widgets when
they are reused or intentionally isolated from role pages:

```text
widgets/
  app-sidebar/
    ui/app-sidebar.tsx
    index.ts
  app-navbar/
    ui/app-navbar.tsx
    index.ts
  order/
    ui/page-wrapper.tsx
    ui/page.tsx
    index.ts          ← export { PageWrapper as OrderPage } from "./ui/page-wrapper"
```

**Does not belong:** Simple UI primitives (→ `shared/ui/`), single-use
page sections (→ keep in the page).

---

## Features Layer

Independent, reusable user interactions. **Create only when used in 2+ places.**

```text
features/
  auth/
    ui/
      LoginForm.tsx
      RegisterForm.tsx
    model/
      auth.ts               ← Auth state + logic
    api/
      login.ts
      register.ts
    index.ts
  add-to-cart/
    ui/
      AddToCartButton.tsx
    model/
      cart.ts
    index.ts
  like-post/
    ui/
      LikeButton.tsx
    model/
      like.ts
    api/
      toggle-like.ts
    index.ts
```

**Feature composition**: features consume entities and are composed in
higher layers:

```typescript
// widgets/post-card/ui/PostCard.tsx
import { UserAvatar } from '@/entities/user';
import { LikeButton } from '@/features/like-post';
import { CommentButton } from '@/features/comment-create';

export const PostCard = ({ post }) => (
  <article>
    <UserAvatar userId={post.authorId} />
    <h2>{post.title}</h2>
    <p>{post.content}</p>
    <div>
      <LikeButton postId={post.id} />
      <CommentButton postId={post.id} />
    </div>
  </article>
);
```

Features commonly expose only UI, and add `model/`, `api/`, or
`lib/` only when the feature needs local state, requests, schemas, or helper
logic:

```text
features/
  notifications/
    ui/notification-toast.tsx
    ui/notifications-toggle.tsx
    model/notifications.constants.ts
    index.ts
  unload/
    ui/page.tsx
    model/unload.store.ts
    lib/validate-date-range.ts
    index.ts
```

---

## Entities Layer

Reusable business domain models. **Create only when used in 2+ places. Starting
without this layer is completely valid.** For this migration, stable legacy
domains may be promoted to entities during the rewrite to match the mature
target architecture.

```text
// Minimal entity: model only (most common form)
entities/user/
  model/
    user.ts                  ← Types + domain logic
  index.ts

// Entity with UI (use with caution)
// ⚠️ Adding UI to entities increases cross-import risk.
// Other entities may want to import this UI, leading to @x dependencies.
// Entity UI should only be imported from higher layers (features, widgets,
// pages), never from other entities.
entities/product/
  model/
    product.ts
  ui/
    ProductCard.tsx
  index.ts
```

Project-style entities usually look like this:

```text
entities/
  order/
    api/
      get-order.ts
      open-dispute.ts
      order.queries.ts
      index.ts          ← exports request functions and `queries`
    model/
      order.types.ts
      order.constants.ts
      order.context.tsx
      order.context.provider.tsx
    ui/
      order-status-indicator.tsx
      open-dispute-modal.tsx
    index.ts            ← public API for types, UI, model, and API namespace
```

Typical public API:

```typescript
export type { Order, OrderStatus } from "./model/order.types";
export { OrderStatusEnum } from "./model/order.types";
export * as orderApi from "./api";
export { OrderStatusIndicator } from "./ui/order-status-indicator";
export { useOrderContext } from "./model/order.context";
```

---

## Shared Layer Structure

Infrastructure with no business logic. Organized by segments only (no slices).
Segments may import from each other.

```text
shared/
  ui/                ← UI kit: Button, Input, Modal, data-table, shadcn wrappers
  lib/               ← Infrastructure libs: axios, react-query, date, websocket
  constants/         ← URLs, sidebar links, app-wide constants
  hooks/             ← Generic hooks not tied to a business domain
  types/             ← Generic response, pagination, utility, and React types
  mocks/             ← Reusable mock data
  tests/             ← Shared test utilities
  api/               ← Optional API primitives when not under shared/lib
  config/            ← Environment variables, app settings when needed
  assets/            ← Branding assets shared across the app (use sparingly)
```

```typescript
// shared/ui/Button/Button.tsx
export const Button = ({ children, onClick, variant = 'primary' }) => (
  <button className={`btn btn-${variant}`} onClick={onClick}>
    {children}
  </button>
);

// shared/ui/Button/index.ts
export { Button } from './Button';
export type { ButtonProps } from './Button';
```

Shared **may** contain application-aware infrastructure (route constants,
HTTP client setup, branding assets, common response types). It must **never**
contain business logic, feature-specific code, or entity-specific code.

For asset placement specifically (images, icons, fonts, PDFs), see
`references/asset-handling.md`.

---

## Segments

A segment groups related code within a slice (or within App/Shared). The
standard segments cover the most common technical purposes:

- **`ui`**: UI display (components, date formatters, styles).
- **`api`**: backend interactions (request functions, data types, mappers).
- **`model`**: data model (schemas, interfaces, stores, business logic).
- **`lib`**: library code that other modules in this slice need.
- **`config`**: configuration files and feature flags.

Custom segments are allowed when needed. In this project family, `shared` may
use `constants/`, `hooks/`, `types/`, `mocks/`, and `tests/`; keep their
contents generic and non-domain-specific.

### Group by what it is *for*, not by what it *is*

Segment names describe **purpose**, not the kind of code they hold. This
is the desegmentation principle:

```text
// ❌ BAD in slice internals: grouping by vague technical kind
shared/
  components/         ← What kind of components?
  utils/              ← Utility for what?
  helpers/            ← Same problem
  actions/            ← Redux actions for what?

// ✅ GOOD: grouping by purpose, with project-specific shared exceptions
shared/
  ui/                 ← For displaying UI
  lib/                ← For infrastructure/library adapters
  constants/          ← For app-wide constants
  hooks/              ← For generic hooks
  types/              ← For generic shared types
```

Inside slices, avoid generic files like `types.ts`, `constants.ts`, and
`utils.ts`. Prefer domain-prefixed files: `order.types.ts`,
`order.constants.ts`, `order.context.tsx`, `unload.store.ts`,
`order.queries.ts`.

This rule applies everywhere: in `shared/`, in slices, and when designing
new custom segments.

## Naming Conventions

### Domain-based file naming

Within a segment, name files after the business domain, not the technical
role:

```text
// ❌ Technical-role naming: mixes domains
model/types.ts          ← Which types? User? Order?
model/utils.ts
api/endpoints.ts
model/selectors.ts

// ✅ Domain-based naming: each file owns one domain
model/user.ts           ← User types + logic + store
model/order.ts          ← Order types + logic + store
model/order.types.ts    ← project style: domain-prefixed type file
model/order.constants.ts
model/order.context.tsx
model/unload.store.ts
api/order.queries.ts
api/fetch-profile.ts    ← Clear what this API does
model/todo.ts           ← Redux slice + selectors + thunks
```

Use kebab-case for component and request files (`order-status-indicator.tsx`,
`get-order.ts`, `open-dispute.ts`) and PascalCase for exported React
components (`OrderStatusIndicator`).

### Single-concern segments

If a segment contains only one domain concern, the filename may match the
slice name:

```text
features/auth/
  model/
    auth.ts          ← Single concern, matches slice name
```

### Index files as public API

Every slice must have an `index.ts` that re-exports its public interface:

```typescript
// entities/user/index.ts
export { UserAvatar } from "./ui/UserAvatar";
export { useUser, type User } from "./model/user";
```

---

## Slice Groups

A **slice group** is a folder that contains related slices on the same
layer, used purely to make the structure easier to navigate as the number
of slices grows. A slice group is **not** a slice itself: it has no
segments (`model/`, `ui/`, `api/`), no public API (`index.ts`), and no
shared code. Slice isolation rules apply unchanged inside a group: sibling
slices in the same group cannot import from each other.

Slice groups are optional. Use them only when the layer has grown large
enough that a flat structure becomes hard to scan and there is an obvious
grouping criterion.

### When to use

- Several slices share the same business context and are scattered across
  the layer.
- The slice names clearly suggest they belong to the same topic.
- The layer has grown to the point where it is hard to scan at a glance.

### When NOT to use

- Names alone are enough for quick navigation.
- There is no natural grouping criterion.
- Only two or three slices would end up in the group.

### Example: grouping payment-related entities

```text
entities/
  payment/                  ← Slice group (no public API)
    invoice/                ← Slice
      model/
      ui/
      index.ts
    receipt/                ← Slice (model/, ui/, index.ts)
    transaction/            ← Slice (model/, ui/, index.ts)
  user/                     ← Slice (not in any group)
  product/                  ← Slice
```

Imports go through the full path:

```typescript
import { Invoice } from "@/entities/payment/invoice";
import { Receipt } from "@/entities/payment/receipt";
```

The same pattern applies to the Pages layer. For example, grouping
`pages/order/{list,detail,create}` when there are multiple pages on the same
topic such as list, detail, create, and edit. This is one possible example
and does not represent the default structure for the Pages layer.

### Features: use with caution

Slice groups can be applied to Features, but features often span multiple
entities and lack a natural grouping criterion. A group like
`features/cart/` tends to attract everything cart-related (DTOs, mappers,
helpers) until it stops being a navigation aid and starts acting as the
home for the entire cart domain, which weakens the principle that
features are split by use case. Before grouping features, check that the
group contains only feature slices and that two or three slices is not the
entire content.

### Anti-patterns

- **Do not put `index.ts` on the group folder.** That promotes the group
  to a slice and breaks the layer's contract.
- **Do not put shared `utils.ts`, `constants.ts`, or `types.ts` files
  inside the group.** A slice group has no shared code. Extract reusable
  code to `shared/` instead. If the layer is `entities` and the shared
  logic is genuinely domain logic, consider whether the boundaries are
  too granular and the slices should be merged into one isolated entity
  (see `references/excessive-entities.md`). The `@x` notation does not
  apply to slice groups. It is a cross-import surface between entity
  slices, not a sharing mechanism for siblings within a group.
- **Do not relax slice isolation inside the group.** If two slices in the
  same group need to share code, extract it one layer down rather than
  adding a `_common/` file.

---

## Path Aliases

Configure path aliases so imports follow the `@/layer/slice` pattern:

```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/app/*": ["src/app/*"],
      "@/pages/*": ["src/pages/*"],
      "@/widgets/*": ["src/widgets/*"],
      "@/features/*": ["src/features/*"],
      "@/entities/*": ["src/entities/*"],
      "@/shared/*": ["src/shared/*"]
    }
  }
}
```

For framework-specific alias configuration (Vite, Next.js, Nuxt, Astro),
see `references/framework-integration.md`.
