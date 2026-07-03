# ARCHITECTURE.md

> Audience: AI coding agents and developers. Normative document.
> Keywords MUST / MUST NOT / SHOULD / NEVER are binding.
> Scope: **project-agnostic** (no business-domain specifics) but **Python-specific** — the rules
> assume an async Python service with type hints, dataclasses, pydantic-style DTOs, a DI
> container, and an async ORM. Porting to another stack = keep the patterns, swap the tools.
> Read this BEFORE creating files or changing project structure.
>
> This file is a TEMPLATE. How it is actually applied to THIS repository — and every deliberate
> deviation from it — lives in [SYSTEM.md](SYSTEM.md), which overrides this file for this project.

## 1. Architectural model

This project combines **Domain-Driven Design (DDD)** with **Vertical Slice Architecture (VSA)**:

- **DDD** defines *what the code means*: the domain layer holds the business model
  (entities, value objects, domain services, events, exceptions) and stays free of I/O and frameworks.
- **VSA** defines *how the code is grouped*: each **use case** is a self-contained folder
  under `features/<feature>/<use_case>/`, not a set of horizontal service/repository layers.

```text
┌──────────────────────────────────────────────────────────┐
│ entrypoint (main)  ←  features/registry (wiring)         │
├──────────────┬───────────────┬───────────────────────────┤
│ features/    │ features/     │ features/                 │
│ <feature>/   │ <feature>/    │ shared/<capability>/      │  ← use cases (VSA)
│  <use_case>/ │  <use_case>/  │  (reused app services)    │
├──────────────┴───────────────┴───────────────────────────┤
│ domain/                                                  │  ← pure business model (DDD)
├──────────────────────────────────────────────────────────┤
│ infrastructure/                                          │  ← DB, integrations, transport glue
└──────────────────────────────────────────────────────────┘
```

## 2. Directory layout (canonical template)

```text
project/
├── domain/                        # Business model. No I/O, no transport.
│   ├── values/                    # Value objects (immutable, self-validating)
│   ├── entities/                  # Entities & aggregate roots; base.py: BaseEntity
│   │                              #   (id, timestamps, record()/collect_events())
│   ├── services/                  # Domain services: multi-entity business calculations
│   ├── events/                    # Domain events (immutable facts, past tense)
│   ├── exceptions/                # Domain exceptions; base.py with the error hierarchy
│   ├── interfaces/                # Ports (ABCs) for EXTERNAL systems & cross-cutting
│   ├── constants/                 # Domain constants
│   └── clock.py                   # Single source of "now" (testable time)
├── features/
│   ├── <feature>/                 # Feature area, e.g. order/, auth/, billing/
│   │   ├── schemas.py             # (optional) response schemas shared by the feature's use cases
│   │   └── <use_case>/            # ONE use case, e.g. create/, get/, cancel/, redeem/
│   │       ├── controller.py      # Transport entry point. Thin.
│   │       ├── subscriber.py      # (alt. entry) reacts to a domain event → calls handler
│   │       ├── task.py            # (alt. entry) scheduled/background trigger → calls handler
│   │       ├── handler.py         # The use case itself. Orchestration only.
│   │       ├── repository.py      # Slice-local data access for THIS use case
│   │       ├── provider.py        # DI provider wiring this slice
│   │       ├── schemas.py         # Input/output DTOs of this use case
│   │       └── admin/controller.py# (optional) privileged transport variant
│   ├── shared/                    # App services reused by 2+ use cases
│   │   └── <capability>/          # e.g. shared/audit_log/
│   │       ├── service.py         # The reusable application service
│   │       ├── repository.py      # Its data access
│   │       └── provider.py        # Its DI provider
│   └── registry/                  # THE composition registry
│       ├── providers.py           # PROVIDERS: list of all DI providers
│       ├── routers.py             # ROUTERS: list of all controllers' routers
│       ├── subscriptions.py       # SUBSCRIPTIONS: event type → subscriber wiring
│       └── tasks.py               # TASKS: scheduled/background task wiring
├── infrastructure/
│   ├── database/                  # Engine/session setup, ORM tables, migrations,
│   │   └── integrity.py           #   DB-constraint → domain-error resolver
│   ├── repositories/base.py       # Generic base repository (CRUD primitives)
│   ├── providers/session.py       # Request-scoped session/Unit-of-Work provider
│   ├── <integration>/             # One folder per external system:
│   │   ├── client.py              #   transport client
│   │   ├── models.py              #   payload models
│   │   └── exceptions.py          #   integration exceptions
│   ├── config/                    # Settings (env-driven)
│   └── logging.py                 # Logging setup (configured by entrypoint)
├── tests/                         # Mirrors source layout
└── main.py                        # Entrypoint: app factory, consumes the registry
```

## 3. The Dependency Rule

Allowed import directions:

| From \ To           | domain | own slice/capability²         | other use-case slice | features/shared | infrastructure | registry |
|---------------------|--------|-------------------------------|----------------------|-----------------|----------------|----------|
| **domain**          | ✅     | —                             | ❌                   | ❌              | ❌             | ❌       |
| **use-case slice**  | ✅     | ✅                            | ❌                   | ✅              | ✅¹            | ❌       |
| **features/shared** | ✅     | ✅                            | ❌                   | ✅              | ✅¹            | ❌       |
| **infrastructure**  | ✅     | —                             | ❌                   | ❌              | ✅             | ❌       |
| **registry / main** | ✅     | providers & entry points only | —                    | ✅              | ✅             | ✅       |

¹ `repository.py` extends the infra base repository; `controller.py`/`provider.py` use transport
and DI glue. `handler.py` SHOULD see infrastructure only through its injected dependencies.
² Files within the same use-case folder (or, for `features/shared`, the same capability folder)
import each other freely.

Hard rules:

- `domain/` MUST NOT import from `features/` or `infrastructure/`. Ever.
- A use-case slice MUST NOT import another use-case slice. The ONLY sanctioned cross-slice
  imports are: `features/shared/` and the feature-level `schemas.py` of its own feature.
- Shared logic moves DOWN (`domain/`) when it is a business concept, or SIDEWAYS into
  `features/shared/` when it is an application capability used by 2+ use cases. Never copy-paste
  a second slice's handler import instead.
- `features/registry/` is wiring only: it imports providers and entry points
  (controllers, subscribers, tasks), contains zero logic.

**Enforcement.** These rules MUST be machine-checked, not just written down: an
[import-linter](https://import-linter.readthedocs.io/) contract (or an equivalent
architecture test) runs in CI and forbids `domain → features/infrastructure` and
slice → slice imports. An unchecked dependency rule will eventually be violated.

## 4. Domain layer (DDD building blocks)

### Value objects — `domain/values/`

- Immutable (`@dataclass(frozen=True, slots=True)`), compared by value.
- Invariants validated in `__post_init__`, documented in the docstring under `Invariants:`.
- Factory classmethods for parsing (`from_string`); invalid instances MUST be unconstructible.

### Entities & aggregates — `domain/entities/`

- `@dataclass(kw_only=True)` extending a common `BaseEntity` (id, timestamps, event recording).
- IDs are time-sortable unique IDs (e.g. UUIDv7), generated in the domain — not by the DB.
- Construction via factory classmethod `create(...)` that enforces invariants; state
  transitions via intention-named methods that guard invariants and record domain events —
  never raw field writes from handlers.
- Fields are domain-typed: statuses as their `StrEnum` (defined next to the entity), money and
  quantities as value objects — not `str`/`float`. An entity in an illegal state MUST be
  unconstructible and unreachable.
- Entities are persistence-ignorant: no ORM base classes, no table metadata, no session
  awareness. Storage mapping lives in infrastructure (§6).

**Aggregates — the consistency boundary.** Every entity belongs to exactly one aggregate;
the aggregate root is the unit the rules below speak about:

- The root is the ONLY public entry point: outside code never mutates a child entity directly,
  and repositories load/save whole aggregates, only via the root.
- Invariants spanning several entities inside the boundary are enforced by the root's methods.
- Aggregates reference OTHER aggregates by ID, never by object:
  `order.customer_id: UUID`, not `order.customer: Customer`.
- One use case modifies ONE aggregate per transaction. Coordinating several aggregates =
  domain events + eventual consistency, not a bigger transaction.
- Keep aggregates small. If a use case only needs values from another aggregate to make a
  decision, pass those values into the method — don't merge the boundaries.

### Domain services — `domain/services/`

- Encapsulate business calculations spanning multiple entities (pricing, billing, policy).
- Pure: inputs in, **decision object** out — a frozen dataclass describing what should happen
  (amounts to charge, dates to move). The HANDLER executes the decision (persists, publishes).
- A domain service holds no repositories and performs no I/O.

### Domain events — `domain/events/`

- Immutable frozen dataclasses, past tense: `OrderPlacedEvent`. Carry IDs, value objects and
  primitives only — never entities, never raw payloads.
- Events are RECORDED where the fact happens: the entity method performing the state
  transition calls `self.record(<Event>)` (provided by `BaseEntity`); the handler collects
  them (`entity.collect_events()`) and hands them to the publisher. A handler constructs an
  event directly only for facts that don't belong to a single entity (e.g. a connection was
  lost, a batch completed).
- Publication timing is governed by §8 "Events and transactions" — recording an event and
  delivering it are separate steps.

### Domain exceptions — `domain/exceptions/`

- Single hierarchy rooted in `base.py` (e.g. `AppError` → `DomainError`, `InfrastructureError`),
  grouped per feature area (`order.py`, `billing.py`).
- Names state the violated rule: `InsufficientBalanceError`, `PromocodeAlreadyRedeemedError`.
- Exceptions are SEMANTIC. Transport mapping (HTTP status, client-safe text) happens in ONE
  central place in infrastructure — never in controllers or handlers.

### Ports — `domain/interfaces/`

- ABCs prefixed `I` (`IEventBus`, `IPaymentGateway`) for EXTERNAL systems and cross-cutting
  concerns: message buses, third-party gateways, connectors.
- Persistence of YOUR OWN data does NOT need a port — use slice-local repositories (§5).
  Abstract the volatile (other people's systems), not the database you own.

### Clock — `domain/clock.py`

- All business code gets "now" from one function (e.g. `now_utc()`). NEVER call
  `datetime.now()` directly in domain or handlers — time must be controllable in tests.

## 5. Features layer (vertical slices)

One **use case** = one folder `features/<feature>/<use_case>/`. Use-case names are verbs or
scenario names: `create/`, `get/`, `cancel/`, `redeem/`, `webhook/`.

### File roles (fixed contract — every slice uses these names)

| File            | Role                                                                                                                  | MUST NOT contain                                                                           |
|-----------------|-----------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| `controller.py` | Entry point: parse input → call handler → map result to response schema (same contract for `subscriber.py`/`task.py`) | Business logic, try/except for domain errors, queries                                      |
| `handler.py`    | The use case: orchestrates repos, domain objects, shared services; returns domain result                              | Framework machinery (request/response objects, routing, headers), SQL, raw payload parsing |
| `repository.py` | Data access for THIS use case: extends the generic base repository, adds use-case-specific queries                    | Queries serving other use cases, business decisions                                        |
| `provider.py`   | DI provider registering this slice's handler + repository                                                             | Logic of any kind                                                                          |
| `schemas.py`    | Input DTO (request/command) and use-case-specific output DTOs                                                         | Behavior, domain invariants                                                                |

Notes:

- The handler's input is the DTO from `schemas.py` (for non-transport entries the DTO is a
  command/query; same file, same rules).
- Deliberate trade-off: the handler accepts the `schemas.py` DTO directly instead of a
  separate command class — one mapping layer less. This is safe because the DTO is data-only;
  framework request/response objects still never reach the handler, and DTO → domain
  conversion happens in the handler's first lines (CODE_STYLE.md §2).
- Response schemas describing a feature's core resource live in the feature-level `schemas.py`
  (e.g. `features/order/schemas.py: OrderResponse`) and are reused by create/get/update/delete.
- A use case omits the files it doesn't need: no transport — no `controller.py`;
  no persistence — no `repository.py`.

### Entry points: `controller.py`, `subscriber.py`, `task.py`

Every use case is triggered through an ENTRY-POINT file that obeys the same thin contract as
a controller — adapt the trigger into the command DTO, call the handler, contain no logic:

- `controller.py` — transport request (HTTP/RPC).
- `subscriber.py` — reaction to a domain event: receives the event, builds the command,
  calls the handler. Registered in `features/registry/subscriptions.py`.
- `task.py` — scheduled or background trigger. Registered in `features/registry/tasks.py`.

One use case MAY have several entry points reusing ONE handler (public + `admin/controller.py`,
webhook + reconciling `task.py`). Same operation through a different trigger = another entry
point in the same slice — never a parallel slice with a copied handler.

### Read vs write slices (CQRS-lite)

Each slice chooses its own depth — this asymmetry is the point of vertical slicing:

- **Write slices** (create/cancel/redeem) take the full path: DTO → domain values → aggregate
  methods → events. All rules of §4 apply.
- **Read slices** (get/list/report) MAY skip the domain entirely: `repository.py` projects
  storage straight into response DTOs, and the handler returns those DTOs. Building entities
  only to serialize them back is waste — don't.
- A read slice makes NO business decisions and emits NO events. The moment a "read" needs a
  business rule, it is a write-shaped use case — route it through the domain.

### Slice granularity

- One use case = one business operation = one transaction shape. `get` and `list` are two
  slices — slices are cheap, merged slices are not.
- Split when triggers, permissions, or transaction shapes differ; keep together when it is
  the same operation arriving through different entry points (one handler, many entries).
- A slice should have exactly one reason to change. If a requirement routinely forces edits
  in two slices at once, their shared concept belongs in `domain/` or `features/shared/`.

**The deletion test:** deleting a use-case folder must break nothing except its lines in
`features/registry/`. If anything else breaks, coupling has crept in — fix the design, not
the symptom.

### Slice-local repositories

- Each use case OWNS its queries. Generic CRUD comes from `infrastructure/repositories/base.py`;
  the slice subclass adds only what this use case needs.
- MUST NOT pile queries for several use cases into one repository — if two use cases need the
  same non-trivial query, that's a `features/shared/` capability.

### `features/shared/` — reused application services

- A capability used by 2+ use cases (audit journal, provisioning sync, ledger) becomes
  `features/shared/<capability>/` with `service.py`, `repository.py`, `provider.py`.
- Shared services own an application-level protocol (ordering of writes, atomicity contract)
  and document it; handlers pass in already-made business decisions, not raw data to interpret.
- Promotion is DELIBERATE: do not create a shared capability for one caller "just in case".
  Small duplication between two slices is acceptable until the third caller appears.

### `features/registry/` — the composition registry

- One module per activation kind: `providers.py` (`PROVIDERS` — every DI provider),
  `routers.py` (`ROUTERS` — every controller router), `subscriptions.py` (`SUBSCRIPTIONS` —
  event type → subscriber), `tasks.py` (`TASKS` — scheduled/background entries).
- `main.py` consumes ONLY the registry. Adding a use case = create the folder + register its
  provider and entry point here. Nothing else in the codebase changes — this is what makes
  the deletion test (§5) hold.

## 6. Infrastructure layer

- **Base repository**: one generic class with CRUD primitives (`add`, `get_one`, `update`, …),
  parameterized by entity type. Slices subclass it; it never contains feature queries.
- **Unit of Work at the boundary**: the DI session provider opens a request-scoped
  session/transaction, COMMITs on success, ROLLBACKs on failure. Handlers and repositories
  MUST NOT commit; they may `flush` to obtain DB-assigned values.
- **Persistence mapping**: ORM table definitions live in `database/tables/`; domain entities
  are bound to them imperatively (or via an explicit mapper) so `domain/` never imports the
  ORM. An entity class MUST NOT inherit from an ORM base or carry table metadata — if the
  mapper can't express something, change the table or the mapper, not the entity.
- **Constraint mapping**: DB integrity errors (unique, FK violations) are resolved to domain
  exceptions in one place (`database/integrity.py`), so callers see business errors, not driver errors.
- **Integration boundary**: each external system gets its own folder with `client.py`,
  `models.py`, `exceptions.py` — never one god-module. Raw payloads are translated to domain
  types inside the integration; they MUST NOT leak into handlers or domain.
- **Central error mapping**: one module registers exception handlers translating the domain
  exception hierarchy into transport responses. Internal context (ids, upstream payloads)
  MUST NOT leak into client-facing messages.

## 7. Request execution flow

```text
transport request
  → controller.py        parse into schemas.py DTO
  → handler.py           map DTO → domain values → load aggregate via repository.py
                         → decide via entity methods / domain services (events recorded)
                         → persist via repositories → call shared services
                         → hand recorded events to the publisher
  → controller.py        map domain result to response schema
  → session provider     commit (or rollback)
  → event dispatcher     deliver recorded events (after commit — see §8)
  → exception handlers   (on error) domain exception → client-safe transport response
```

## 8. Cross-slice communication

- **Synchronous, transactional** (must happen in the same unit of work): call a
  `features/shared/<capability>/` service.
- **Decoupled, reactive** (other slices may care, this one shouldn't know): publish a domain
  event via the `IEventBus` port; subscribers register at composition time.
- NEVER import another use case's handler.

### Events and transactions

The split — atomic work is a service call, reactive work is an event — is a hard rule:

- Domain events are dispatched to subscribers AFTER the unit of work commits. A subscriber
  MUST never observe state that can still roll back, and a failing subscriber MUST NOT roll
  back the use case that emitted the event.
- If a reaction MUST be atomic with the change (same transaction, all-or-nothing), it is NOT
  an event subscriber — the handler calls a `features/shared/` service explicitly.
- After-commit delivery is in-memory: a crash between commit and dispatch loses the event.
  When losing the event corrupts business state (financial postings, provisioning), use a
  **transactional outbox**: persist the event in the same transaction, relay it asynchronously.
  For best-effort reactions (notifications, cache warming) the outbox is overkill — skip it.
- Subscribers are idempotent: the same event may be delivered more than once.

## 9. Decision table: where does this code go?

| You are writing…                        | Put it in                                                                               |
|-----------------------------------------|-----------------------------------------------------------------------------------------|
| A business rule or invariant            | `domain/` (entity, value object, or domain service)                                     |
| A calculation spanning several entities | `domain/services/`, returning a decision object                                         |
| A fact other slices must react to       | Domain event recorded by the entity, dispatched after commit (§8)                       |
| A new user-facing capability / use case | `features/<feature>/<use_case>/` (5-file contract)                                      |
| A read-only view (get/list/report)      | Read slice: `repository.py` projects into response DTOs, domain skipped (§5)            |
| A reaction to a domain event            | `subscriber.py` in the reacting use case, registered in `registry/subscriptions.py`     |
| A change to an existing use case        | That slice only                                                                         |
| A query needed by exactly one use case  | That slice's `repository.py`                                                            |
| Logic/queries needed by 2+ use cases    | `features/shared/<capability>/` (if application-level) or `domain/` (if business-level) |
| Talking to an external system           | `infrastructure/<integration>/`, behind a `domain/interfaces/` port                     |
| Mapping errors to transport responses   | Central exception-handler module in infrastructure                                      |
| Wiring objects together                 | Slice `provider.py`, aggregated in `features/registry/`                                 |
| App startup / shutdown                  | `main.py`                                                                               |

## 10. Anti-patterns (NEVER do these)

| Anti-pattern                                                              | Correct move                                                                         |
|---------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| Horizontal layers: `services/`, `managers/`, `utils/`                     | Logic into a slice handler, domain service, or `features/shared/`                    |
| One use case importing another's handler/repository                       | `features/shared/` service or domain event                                           |
| God repository serving many use cases                                     | Slice-local repositories on the generic base                                         |
| Business rules in controllers or `repository.py`                          | Push into domain entities/services; handler orchestrates                             |
| `try/except` + status codes inside controllers                            | Raise domain exceptions; central handlers map them                                   |
| Handler calling `commit()`                                                | Unit of Work commits at the boundary                                                 |
| `datetime.now()` scattered through business code                          | `domain/clock.py`                                                                    |
| Entity inheriting an ORM base / table metadata in `domain/`               | Persistence-ignorant entity; imperative mapping in infrastructure (§6)               |
| Modifying two aggregates in one transaction                               | One aggregate per use case; coordinate via domain events (§4, §8)                    |
| Dispatching events to subscribers before commit                           | Record on the entity; dispatch after the unit of work commits (§8)                   |
| Holding another aggregate as an object field                              | Reference by ID; pass needed values into the method (§4)                             |
| Loading entities just to map them into a response DTO                     | Read slice: project storage straight into the response (§5)                          |
| Copying a slice because the trigger differs (webhook vs schedule)         | One handler, several entry points in the same slice (§5)                             |
| Raw dict/JSON passed through handlers or domain                           | Translate to domain types inside the integration/adapter                             |
| Backward-compat shims: alias routes, proxy modules, deprecated re-exports | Change the contract explicitly; update all callers, tests, and docs in the same task |
| Registering a feature anywhere besides the registry                       | `features/registry/providers.py` + `routers.py` only                                 |
