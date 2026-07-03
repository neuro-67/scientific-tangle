# CODE_STYLE.md

> Audience: AI coding agents and developers. Normative document.
> Read this BEFORE writing or editing code. Structure rules live in [ARCHITECTURE.md](ARCHITECTURE.md).
> Scope: project-agnostic but **Python-specific** (modern async Python: dataclasses,
> pydantic-style DTOs, a DI container, an async ORM).
> Examples are illustrative (generic `order` feature) — apply the patterns, not the example names.

## 0. Guiding principle

Prefer the simplest code that satisfies these rules: no speculative abstraction, no
duplication, no code without a caller. Brevity is a result of clarity, never a goal that
overrides it.

## 1. Naming

| Element             | Convention                                               | Example                                  |
|---------------------|----------------------------------------------------------|------------------------------------------|
| Feature folder      | `snake_case` noun                                        | `order/`, `promocode/`                   |
| Use-case folder     | `snake_case` verb / scenario                             | `create/`, `redeem/`, `webhook/`         |
| Handler             | `<Verb><Noun>Handler`                                    | `CreateOrderHandler`                     |
| Repository (slice)  | `<Verb><Noun>...Repository` or `<Noun>Repository`        | `CreateOrderRepository`                  |
| DI provider         | `<Verb><Noun>Provider`                                   | `CreateOrderProvider`                    |
| Request/command DTO | `<Verb><Noun>Request` / `Command`                        | `CreateOrderRequest`                     |
| Query DTO (reads)   | `<Verb><Noun>Query`                                      | `ListOrdersQuery`                        |
| Event subscriber    | `<Verb><Noun>OnEventSubscriber` or `<UseCase>Subscriber` | `SyncStockOnOrderPlacedSubscriber`       |
| Response DTO        | `<Noun>Response`                                         | `OrderResponse`                          |
| Domain event        | Past tense + `Event`                                     | `OrderPlacedEvent`                       |
| Domain exception    | Rule violated + `Error`                                  | `InsufficientBalanceError`               |
| Port (interface)    | `I` + role                                               | `IPaymentGateway`                        |
| Domain service      | `<Concern>Service` + decision dataclass                  | `BillingService`, `TariffChangeDecision` |
| Constants           | Prefixed by the file's concept                           | `REFUND_POLICY_EN`, not `TEXT_EN`        |

- Names come from the ubiquitous language. If the business says "settlement", the code says
  `settlement` — not `processing`.
- NEVER: `Manager`, `Util`, `Helper`, `Processor`, `Data`, `Info`, `do_stuff`. (`Service` is
  reserved for domain services and `features/shared/` application services only.)
- No magic numbers or repeated string literals — named constants, `StrEnum`, or config.

## 2. Canonical slice (copy these shapes)

### `schemas.py` — DTOs only

```python
class CreateOrderRequest(BaseModel):
    """Input for the create-order use case."""

    customer_id: UUID
    items: list[OrderItemInput]
```

- Response models for the feature's core resource live in feature-level `schemas.py`
  and set `model_config = {"from_attributes": True}` so controllers can `model_validate(entity)`.
- Schemas validate SHAPE (types, ranges, required fields); domain objects enforce BUSINESS
  invariants. Don't duplicate domain rules in validators.
- Schema objects never cross into `domain/`: the handler converts DTO fields to domain
  values/entities at its entrance, and converts nothing back — it returns domain objects.

### `handler.py` — the use case

```python
class CreateOrderHandler:
    """Creates an order from a validated request."""

    def __init__(self, repo: CreateOrderRepository, event_bus: IEventBus) -> None:
        self._repo = repo
        self._event_bus = event_bus

    async def __call__(self, command: CreateOrderRequest) -> Order:
        items = [OrderItem(sku=Sku(i.sku), quantity=i.quantity) for i in command.items]
        order = Order.create(customer_id=command.customer_id, items=items)
        await self._repo.add(order)
        await self._event_bus.publish_after_commit(order.collect_events())
        return order
```

- Constructor injection only; dependencies stored as `_private` attributes.
- One public method `__call__(command) -> domain result`. Write handlers return
  entities/values — never response schemas, never transport types. (Read handlers are the
  exception — see "Read slice" below.)
- First step: map DTO fields to domain values (`Sku(i.sku)` above). Pydantic models go no
  deeper than the handler's first lines.
- Orchestration only: load → decide via domain → persist → notify. A business `if` in a
  handler belongs in an entity, value object, or domain service.
- Events come FROM the entity (`order.collect_events()`); the bus delivers them after the
  unit of work commits ([ARCHITECTURE.md §8](ARCHITECTURE.md#8-cross-slice-communication)).
- No `commit()` — the Unit of Work at the boundary owns the transaction. `flush()` via the
  repository is allowed when a DB-assigned value is needed.

### `repository.py` — slice-local data access

```python
class CreateOrderRepository(SQLAlchemyRepository[Order]):
    """Order persistence for the create use case."""

    model_type = Order

    async def exists_active_for_customer(self, customer_id: UUID) -> bool:
        ...
```

- Extend the generic base repository; add ONLY the queries this use case needs.
- Returns domain entities/values. No business decisions inside queries.

### `controller.py` — thin transport endpoint

```python
router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_order(
    body: CreateOrderRequest,
    handler: FromDishka[CreateOrderHandler],
) -> OrderResponse:
    """Create a new order."""
    entity = await handler(body)
    return OrderResponse.model_validate(entity)
```

- Exactly: declare route → call handler → map to response. No try/except, no queries, no logic.
- Status codes via framework constants (`status.HTTP_201_CREATED`), never bare numbers.
- REST conventions: plural resources (`/orders`), nesting max one level, methods match
  semantics (POST create / GET read / PATCH partial update / DELETE remove).

### API documentation (Swagger / OpenAPI)

Every endpoint MUST be visible in Swagger with just enough context for a frontend developer
to call it — no more.

- **`summary`** on the decorator: 3–7 words, imperative. `summary="Create user"`, not
  `"Endpoint to create a new user in the system"`.
- **`description`** only when the summary is not self-explanatory (auth requirements,
  side effects, non-obvious behavior). One or two sentences, no marketing prose.
- **Docstring** on the handler function mirrors the summary — don't repeat it three times.
- **`tags`** on the router group related use cases: `tags=["auth"]`, `tags=["users"]`.
- **`response_model`** on every route so the response shape appears in the schema.
- Enumerate non-2xx outcomes with `responses={...}` only when the frontend needs to switch
  on them (e.g. 409 conflict, 403 forbidden with envelope). Don't list every possible 500.
- **`include_in_schema=False`** on internals the client shouldn't see — most notably auth
  cookies pulled via `Cookie(alias=..., include_in_schema=False)`. Cookies live in
  `Cookie` headers set by prior calls; they are not user-supplied parameters.
- **All POST endpoints take a JSON body** — never `Form`, never query params for input.
  A pydantic DTO from the slice's `schemas.py`, with sensible defaults for dev when they
  exist (e.g. login → `admin` / `admin` for the seeded dev admin).

Rule of thumb: if a developer opening `/docs` needs to read the source to figure out how
to call the endpoint, the doc is too sparse. If they skim past the description, it is too
verbose.

### `provider.py` — DI wiring

```python
class CreateOrderProvider(Provider):
    """DI provider for the create-order slice."""

    scope = Scope.REQUEST
    repository = provide(CreateOrderRepository)
    handler = provide(CreateOrderHandler)
```

Then register the provider and the entry point in `features/registry/`.

### Read slice variant (get/list/report)

```python
class ListOrdersHandler:
    """Lists a customer's orders as response DTOs."""

    def __init__(self, repo: ListOrdersRepository) -> None:
        self._repo = repo

    async def __call__(self, query: ListOrdersQuery) -> list[OrderSummaryResponse]:
        return await self._repo.list_summaries(customer_id=query.customer_id)
```

- The read repository projects storage straight into response DTOs — no entities, no events,
  no business decisions ([ARCHITECTURE.md §5](ARCHITECTURE.md#5-features-layer-vertical-slices)).
- The controller returns the handler's result as-is.

### `subscriber.py` — event-driven entry point

```python
class SyncStockOnOrderPlacedSubscriber:
    """Adapts OrderPlacedEvent into the sync-stock use case."""

    def __init__(self, handler: SyncStockHandler) -> None:
        self._handler = handler

    async def __call__(self, event: OrderPlacedEvent) -> None:
        await self._handler(SyncStockCommand(order_id=event.order_id))
```

- Same thin contract as a controller: adapt the event into the command, call the handler,
  no logic. Registered in `features/registry/subscriptions.py`. Must be idempotent
  (events can be delivered more than once).

## 3. Domain objects

### Entity (aggregate root)

```python
class OrderStatus(StrEnum):
    """Lifecycle states of an order."""

    NEW = "new"
    CANCELLED = "cancelled"


@dataclass(kw_only=True)
class Order(BaseEntity):
    """A customer's order. Aggregate root for its items."""

    customer_id: UUID  # another aggregate — referenced by ID only
    status: OrderStatus
    items: list[OrderItem]

    @classmethod
    def create(cls, *, customer_id: UUID, items: list[OrderItem]) -> Self:
        """Factory enforcing creation invariants."""
        if not items:
            raise EmptyOrderError()
        order = cls(customer_id=customer_id, status=OrderStatus.NEW, items=items)
        order.record(OrderPlacedEvent(order_id=order.id, customer_id=customer_id))
        return order

    def cancel(self, reason: CancelReason) -> None:
        """State transition guarding the lifecycle invariant."""
        if self.status is not OrderStatus.NEW:
            raise OrderAlreadyClosedError(self.id)
        self.status = OrderStatus.CANCELLED
        self.record(OrderCancelledEvent(order_id=self.id, reason=reason))
```

- `kw_only=True`, extends `BaseEntity` (id, timestamps, `record()`/`collect_events()`).
  IDs: time-sortable UUIDs (UUIDv7), generated in domain code.
- Fields are domain-typed: `status: OrderStatus` (a `StrEnum` next to the entity), money and
  quantities as value objects — never bare `str`/`float`.
- Other aggregates are referenced by ID (`customer_id: UUID`), never held as objects.
- Mutations via intention-named methods that guard invariants and `record()` the resulting
  domain event — handlers never write fields directly.
- Persistence-ignorant: no ORM base classes, no table metadata. Mapping lives in infrastructure.

### Value object

- `@dataclass(frozen=True, slots=True)`; invariants in `__post_init__`, documented under
  `Invariants:` in the docstring; factory classmethods returning `Self`. No I/O, no `dict` fields.

### Domain service

- Stateless class (config values allowed); pure calculation in, frozen **decision dataclass** out.
  The handler executes the decision. No repositories, no I/O inside.

### Time

- All "now" via `domain/clock.py` (`now_utc()`). NEVER `datetime.now()` in domain or handlers.

## 4. Errors

- Business violations raise domain exceptions from the single hierarchy in
  `domain/exceptions/` (`base.py` root + one module per feature area).
- Controllers and handlers DO NOT catch domain exceptions — central exception handlers map
  them to transport responses with client-safe messages (no internal ids/payloads leaked).
- DB integrity errors are translated to domain exceptions in one resolver module — never
  caught ad-hoc in handlers.
- NEVER `except Exception: pass`. Broad catches only at runtime boundaries (event-bus dispatch,
  task loops), always logged with context.
- Message format: rule + offending value — `f"base and quote must differ, got {raw!r}"`.

## 5. Typing

- Full annotations on every signature, including `-> None`.
- Modern syntax: `list[str]`, `X | None`, `Self`, `type[T]`, PEP 695 generics. No `typing.List`/`Optional`.
- `Any` only at infrastructure boundaries. Code MUST pass the type checker with zero new errors.

## 6. Logging

- Per-module logger: `logger = logging.getLogger(__name__)`. Configuration happens ONLY in the
  entrypoint — importing a module MUST NOT configure logging or perform any other side effect.
- Domain objects stay log-free. Log in handlers and infrastructure with identifying context (ids).
- NEVER log secrets, credentials, or full raw payloads at `info` and above.

## 7. Async

- I/O-bound code is `async def` end-to-end; no blocking I/O in async paths.
- Long-running work: named tasks (`asyncio.create_task(coro, name=...)`) with an owner that
  awaits/cancels them on shutdown.
- Cleanup that must survive cancellation (rollback, close) is shielded (`asyncio.shield`) and
  the reason documented.

## 8. Imports and modules

- Absolute imports from the project root; order stdlib → third-party → first-party (linter-enforced).
- Every import you write must be used. No lazy imports inside functions without a stated reason.
- One concept per file. Integrations split into `client.py` / `models.py` / `exceptions.py`.
- `__init__.py` empty or deliberate re-export only; no logic.
- NO backward-compatibility shims: alias methods, proxy modules, deprecated re-exports,
  typo-alias routes. Rename = update every caller, test, and doc in the same task.

## 9. Docstrings and comments

- Docstring on every module, class, and public method — describing INTENT, not restating the
  name. Domain objects document `Invariants:`; shared services document their protocol
  (ordering, atomicity contract).
- Comments explain WHY (constraints, non-obvious decisions). No commented-out code, no
  changelog comments. `TODO:` must state the concrete problem.
- Comment only what the code cannot say itself; if the code can be made clear instead of
  commented, do that.

## 10. Tests

- Layout mirrors source: `tests/domain/...`, `tests/features/<feature>/<use_case>/...`.
- Domain tests: pure unit tests, no mocks — construct objects, assert invariants and decisions.
- Use-case tests: drive the HANDLER through its command (with in-memory/fake adapters), not just
  the schemas. Behavior change in a handler ⇒ handler-level or integration test, mandatory.
- Names state behavior: `test_rejects_order_with_no_items`. One behavior per test.
- A broken test is fixed by fixing code or honestly updating the test — never by weakening
  asserts or adding compat shims.

## 11. Formatting & tooling

- Formatter and linter own the layout — never hand-format against them; run the project's
  lint/format/typecheck/test commands before declaring work done. Zero new warnings.

## 12. Self-review checklist

1. New files follow the 5-file slice contract and the [decision table](ARCHITECTURE.md#9-decision-table-where-does-this-code-go)?
2. Slice registered in `features/registry/`? No imports between use-case slices?
3. Business rules in domain objects/services — not in handlers, controllers, or queries?
4. No commits in handlers; errors raised as domain exceptions, mapped centrally?
   Events recorded on entities and dispatched after commit; one aggregate modified per use case?
5. Types complete; type checker, linter, formatter, tests all clean?
6. Tests cover new invariants and the use case's happy + failure paths at handler level?
7. Docs in `/docs` still accurate for what you changed? If not — update them in this task.
