# Excessive Entities

How to keep the `entities` layer clean and avoid over-extracting business
logic into entities. Excessive entities cause ambiguity (what code belongs
where), coupling, and constant import dilemmas as code scatters across
sibling entities.

For this project, apply this guidance together with the mature target
architecture: many stable entities and entity-owned APIs are expected. Avoid
premature entities for speculative code, but do not force stable legacy domains
back into pages just because the first migrated consumer is temporarily
single-use.

## Why this matters

The `entities` layer is one of the lower layers and is widely accessible.
Every layer except `shared` can import from it. That global nature means
changes to `entities` propagate widely, requiring careful design to avoid
costly refactors. Adding an entity is cheap; removing one after many
consumers depend on it is expensive.

## How to keep entities clean

### 0. Consider having no entities layer

An FSD application without an `entities` layer is still FSD. Skipping the
layer simplifies the architecture and keeps it available for future scaling.

**Thin clients** (where the backend handles most data processing and the
client mostly exchanges data) usually do not need an entities layer.
**Thick clients** (significant client-side business logic) are better
candidates for entities.

The classification is not strictly binary. Different parts of the same
application may behave as thick or thin clients.

```text
// Thin client without entities layer (still valid FSD)
src/
  app/
  pages/
    dashboard/
    profile/
  shared/
    api/
    ui/
```

### 1. Avoid preemptive slicing

FSD v2.1 encourages **deferred decomposition** of slices. Place code in the
`model` segment of the consuming page, widget, or feature first. Move it to
`entities` later, when business requirements stabilize and reuse is
confirmed across multiple consumers.

The later code moves to `entities`, the less dangerous the refactor. Code
in `entities` can affect every higher-layer slice that imports it.

During migration, a domain can be extracted earlier when it is already a stable
concept in the legacy codebase and matches a project entity boundary, for
example employee, payment, salary, PVZ, approval, request, notification, or
session. Treat this as migration of an existing domain, not preemptive slicing.

```text
// Iteration 1: code lives where it is used
pages/profile/
  model/
    profile-validation.ts    ← page-specific for now

// Iteration 2 (after the same logic is needed in 2+ places):
entities/profile/
  model/
    profile-validation.ts    ← extracted only after reuse is real
```

### 2. Avoid unnecessary entities

Do not create an entity for every piece of business logic. Use types from
`shared/api` and place logic in the `model` segment of the current slice.
For genuinely reusable business logic, use the `model` segment within an
entity slice while keeping data definitions in `shared/api`.

```text
shared/
  api/
    endpoints/
      order.ts              ← OrderDto type and request functions

entities/
  order/
    model/
      apply-discount.ts     ← Business logic that uses OrderDto
    index.ts
```

The DTO lives in `shared/api/endpoints/order.ts`. Business logic that
operates on it (calculating discounts, applying promotions) lives in
`entities/order/model/`. Do not mirror every API endpoint with a
corresponding entity.

### 3. Exclude CRUD operations from entities

CRUD operations often involve boilerplate code without significant business
logic. In a small/minimal FSD project, putting them in `entities` can clutter
the layer and obscure the code that genuinely matters. Place generic CRUD
in `shared/api`:

```text
shared/
  api/
    client.ts
    endpoints/
      order.ts          ← getOrder, createOrder, updateOrder, deleteOrder
      products.ts       ← Standard CRUD for products
      cart.ts           ← Standard CRUD for cart
    index.ts
```

For complex CRUD with atomic updates, rollbacks, or transactions, evaluate
whether the operation is genuinely business logic. If so, the `entities`
layer may be appropriate. If not, keep it in `shared/api`.

Project convention: stable domain request functions live in
`entities/<domain>/api/`, including list/detail/create/update operations, and
are exposed via `export * as <domain>Api from "./api"`. Follow that convention
for stable domains. Keep Shared for HTTP client infrastructure, interceptors,
generic response types, and truly generic helpers.

### 4. Store authentication data in shared

Prefer `shared` over creating a `user` entity for auth tokens and session
DTOs. These are context-specific to authentication and unlikely to be
reused outside that scope. Wrapping a login response in a `user` entity
also tends to drag entities into cross-layer imports or `@x` chains,
complicating the architecture.

The project convention for this codebase family differs: prefer
`entities/session` for session/auth API, current-session query, and session
context; use `entities/user` for reusable user and role domain types. Keep only
pure token-storage or HTTP interceptor infrastructure in Shared.

The Auth guide also documents **In Entities** (a `user` entity) as a
valid placement when the project already has an entities layer and the
data is genuinely reused. **In Pages/Widgets** is discouraged for both
guides.

**`shared/auth` (or `shared/api`) is the recommended default.** Choose
it when:

- The project has no entities layer yet
- Auth state is just a token plus minimal user info (id, email, role)
- Token management logic (refresh, expiration) is the main concern, not
  user profile data

```text
shared/
  auth/
    use-auth.ts         ← Token + minimal user info
    index.ts
  api/
    client.ts           ← API client reads token from shared/auth
    endpoints/
      order.ts
    index.ts
```

This approach pairs naturally with an API client middleware that injects
the token into authenticated requests.

Use this shared-auth default only if the code is pure infrastructure and has no
session-domain meaning. Otherwise, follow the `entities/session` target shape.

**A `user` entity is the right call when:**

- The project already has an entities layer
- Auth and profile data are tightly coupled (current user info is reused
  across pages for non-auth purposes like comments, posts, mentions)
- Token management has complex business logic (invalidation policies,
  multi-device session tracking) that benefits from co-location with the
  user model

```text
entities/
  user/
    model/
      current-user.ts   ← Token + full user model + business logic
      user.ts           ← Generic user type, used for other users too
    api/
      get-current-user.ts
    index.ts
```

When using the entity approach, the API client (in `shared/api`) needs
access to the token without violating the import rule. The official Auth
guide describes three solutions: pass the token manually on each request,
expose it through a context or `localStorage` with the key kept in
`shared/api`, or inject the token into the API client whenever the entity
store updates.

**Pages and widgets are discouraged.** Avoid placing the token store in a
page's `model/` segment or in a widget. App-wide state belongs in Shared
or Entities, not in route-bound or block-bound layers.

### Decision summary

| Project state | Recommended location |
| --- | --- |
| No entities layer (yet), simple token + minimal user info | `shared/auth` |
| Mature project app | `entities/session` + `entities/user` |
| Entities layer exists, auth and profile tightly coupled | `entities/user` |
| Complex token logic, no profile reuse yet | `shared/auth` (split from `shared/api`) |
| Token storage in a single page or widget | Avoid; promote to Shared or Entities |

A `user` entity created **only** to wrap a login response is premature.
Wait until profile data is consumed for non-auth purposes (avatars in
comments, names in posts) before introducing the entity.

### 5. Minimize cross-imports

FSD permits cross-imports between entities via `@x`, but they introduce
technical issues including circular dependencies. Design entities within
**isolated business contexts** so cross-imports become unnecessary.

**Non-isolated context (avoid):**

```text
entities/
  order/
    @x/
    model/
  order-item/
    @x/
    model/
  order-customer-info/
    @x/
    model/
```

Three sibling entities all referencing each other through `@x`. This is a
sign that the boundaries are wrong.

**Isolated context (preferred):**

```text
entities/
  order-info/
    model/
      order-info.ts    ← order, items, and customer info together
    index.ts
```

One entity encapsulates the related logic. No `@x`, no cross-imports,
no circular dependency risk.

The general rule: when several entities have `@x` dependencies on each
other, treat that as a signal to merge the boundaries, not as something to
manage.

## Decision tree for AI agents

```text
A new piece of business logic needs a home.
  │
  ├─ Is the project a thin client?
  │   └─ YES → Skip entities. Place in shared/ + page model.
  │
  ├─ Is the logic used in only one place right now?
  │   └─ YES → Keep in the consuming slice's model/. Defer extraction.
  │
  ├─ Is it a CRUD operation without business meaning?
  │   ├─ mature stable domain? → entities/<domain>/api/
  │   └─ small/minimal/generic helper? → shared/api/endpoints/<resource>.ts
  │
  ├─ Is it auth data (tokens, session, login DTOs)?
  │   ├─ mature project migration?
  │   │   └─ YES → entities/session/; reusable roles/types → entities/user/
  │   ├─ Project has no entities layer yet?
  │   │   └─ YES → shared/auth/
  │   ├─ Auth and profile data tightly coupled, entities layer exists?
  │   │   └─ YES → entities/user/
  │   └─ Otherwise → shared/auth/ (default).
  │       Avoid placing in a page or widget.
  │
  ├─ Is it just a TypeScript type for an API response?
  │   └─ YES → shared/api/. No entity needed for types alone.
  │
  └─ Is it reusable domain logic confirmed in 2+ consumers?
      └─ YES → Create entities/<name>/model/.
               Verify the boundary is isolated and does not require @x
               to communicate with sibling entities.
```

## Anti-patterns

- **Creating entities preemptively.** Wait for confirmed reuse in 2+
  consumers, not anticipated reuse.
- **Mirroring every API endpoint with an entity in a minimal app.** Generic API
  endpoints can belong in `shared/api`. In this project style, stable domain
  endpoints intentionally live in `entities/<domain>/api/`; do not move those
  to Shared just because they are CRUD-like.
- **Creating a `user` entity *only* to wrap a login response.** A `user`
  entity is justified when profile data is reused across non-auth flows
  (avatars in comments, names in posts) or when token logic is genuinely
  tied to user business logic. In mature project-style apps, prefer
  `entities/session` for login/session data and keep `entities/user` for user
  and role domain types. Storing tokens in a page or widget is discouraged
  regardless of the project shape.
- **Splitting one domain into many entities (`order`, `order-item`,
  `order-customer-info`).** This produces `@x` chains. Merge into a single
  isolated context (`order-info` or `order`).
- **Putting generic CRUD wrappers in entities.** Generic wrappers clutter the
  layer and belong in Shared. Stable domain request functions in this project
  style belong in `entities/<domain>/api/`.

## See also

- `references/cross-import-patterns.md`: how to handle cross-imports when
  they appear, and why `@x` is a last resort.
- `references/layer-structure.md`: layer responsibilities and the entities
  segment shape.
