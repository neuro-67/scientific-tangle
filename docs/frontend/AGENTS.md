Always read the architecture instructions in [AGENTS](AGENTS/) before changing code.
Write new code according to FSD architecture

Agent behavior:
- Do not start a dev server unless the user explicitly asks for it.
- Do not open the browser, Browser plugin, or any local app URL unless the user explicitly asks for it.
- Do not run manual UI checks or exploratory verification without an explicit user request.

1) Separate every component into its own file
2) Do not write components that take more than 500 lines of code. If the component is >500 lines of code, break it into logically separate components. This line limit does not apply to shared/ui components.
3) Put component props type into the same file as the component itself, and name it just Props
4) Use shadcn components in most cases, do not write plain inputs, textareas, dialogs etc. 
5) All non-props types must be stored inside *.types.ts file in model directory
6) Most helper functions should be stored in /lib directory of the current slice (ex. for page shift-schedule its /pages/shift-schedule/lib)
7) DO NOT use constant-colors like text-red-500, text-blue-300, use globally defined variables from index.css file, if the color you want is not present in it, ask user if you should add it or use different color. The purpose of each color also defined in comments of index.css file

Project conventions:
- Do not use TypeScript `interface`; always use `type` for object shapes and contracts.
- Keep types in `*.types.ts` files (except component-specific types like Props or something that is needed only inside single component, this you can keep in a component file itself).
- Keep constants only in `*.constants.ts` files.
- Do not mix constants into `*.types.ts` files or types into `*.constants.ts` files.

API layer rules:
- Write API code the same way as in `frontend_2`: one request = one file inside `entities/<domain>/api/`.
- API files must be thin. They may only call `API.get`, `API.post`, `API.patch`, `API.put`, or `API.delete` and return `r.data`.
- Do not put business logic into API files. No mapping, filtering, aggregation, pagination loops, date conversion, fallback logic, cache variables, or composing several requests inside an API file.
- Do not call another API function from an API file. For example, `getEmployeeActiveShift` must call `API.get(...)` directly, not `getActualShifts(...)`.
- Request params/body type must be named `Req` and declared in the same API file.
- Response type must be named `Res` and declared in the same API file.
- `Req` may be exported if query factories or callers need it. `Res` usually stays local unless it is truly reused outside the file.
- Do not create separate API params type files like `shift-api-params.types.ts`. Put request/response types in the API file as `Req`/`Res`; move a type to `model/<domain>-api.types.ts` only if it is a real domain response type reused in several places.
- API functions should not be `async` unless there is a strong reason. Prefer direct promise chaining:
	`API.get<Res>("/path", { params }).then((r) => r.data)`.
- Use shared axios instance only from `@/shared/lib/axios`.
- Export every request from `entities/<domain>/api/index.ts`.
- Export API namespace from the entity public API: `export * as <domain>Api from "./api";`.

TanStack Query rules:
- All server-state reads in hooks/components must use `useQuery` from `@tanstack/react-query`.
- All server mutations in hooks/components must use `useMutation` from `@tanstack/react-query`.
- Query factories must live in `entities/<domain>/api/<domain>.queries.ts` and use `queryOptions`.
- Query factories call only thin API functions from the same entity API directory.
- Do not create custom files like `schedule-query.helpers.ts` to hide fetching logic. Use entity query factories directly in hooks/components.
- Cross-entity data composition belongs in hooks, pages, widgets, or `lib/` builders, not in `api/`.

Error handling rules:
- For API errors in UI/hooks, use the global `handleApiError` helper from `@/shared/lib/api-error`.
- `handleApiError(error, options)` extracts backend messages from `details[].message`, `detail`, `message`, and `error`, shows a shadcn/sonner error toast by default, and returns the normalized message string.
- Use `handleApiError(error, { fallback: "..." })` in mutation `onError` handlers when a toast should be shown.
- Use `handleApiError(error, { fallback: "...", showToast: false })` when only a string is needed and a toast would be duplicated, for example derived query error text in render.
- Do not create local Axios error parsers such as `extractErrorMessage` inside features/pages. Reuse `@/shared/lib/api-error` instead.

Canonical API file example:

```ts
import { API } from "@/shared/lib/axios";
import type { PaginatedResponse } from "@/shared/api";
import type { ActualShift } from "../model/shift-api.types";

export type Req = {
	employee_id: number;
};

type Res = PaginatedResponse<ActualShift>;

export const getEmployeeActiveShift = ({ employee_id }: Req) =>
	API.get<Res>("/shifts", {
		params: {
			employee_id,
			is_active: true,
			page: 1,
			size: 1,
		},
	}).then((r) => r.data);
```

Canonical query factory example:

```ts
import { queryOptions } from "@tanstack/react-query";
import { getEmployeeActiveShift, type Req as GetEmployeeActiveShiftReq } from "./get-employee-active-shift";

export const queries = {
	all: () => ["shift"],
	actual: () => [...queries.all(), "actual"],
	employeeActive: (query: GetEmployeeActiveShiftReq) =>
		queryOptions({
			queryKey: [...queries.actual(), "employee-active", query.employee_id],
			queryFn: () => getEmployeeActiveShift(query),
		}),
};
```

Canonical usage example:

```ts
const activeShiftQuery = useQuery(shiftApi.queries.employeeActive({ employee_id }));

const openShiftMutation = useMutation({
	mutationFn: shiftApi.openShift,
	onSuccess: () => {
		void queryClient.invalidateQueries({ queryKey: shiftApi.queries.actual() });
	},
});
```
