# Frontend — «Научный клубок»

React 18 + TypeScript + Vite SPA. Организован по **Feature-Sliced Design (FSD)**;
правила и конвенции — в [`docs/frontend/`](../docs/frontend/).

## Стек

- **Vite 6** + **React 18** + **TypeScript** (strict).
- **React Router** — маршрутизация (`createBrowserRouter`).
- **TanStack Query** — серверный стейт, кэш, статусы загрузки.
- **shadcn/ui** + **Tailwind CSS** — UI-кит (см. `src/app/styles/index.css`).
- **axios** — общий инстанс с JWT-интерсептором (`@/shared/lib/axios`).

## Запуск

```bash
cp .env.example .env      # при необходимости поправить VITE_API_BASE_URL
pnpm install
pnpm dev                  # http://localhost:5173
```

Dev-сервер проксирует `/api` на FastAPI (`http://localhost:8000` по умолчанию,
переопределяется через `VITE_PROXY_TARGET`).

## Команды

| Команда          | Назначение                          |
| ---------------- | ----------------------------------- |
| `pnpm dev`       | Дев-сервер с HMR                    |
| `pnpm build`     | Type-check (`tsc -b`) + прод-сборка |
| `pnpm preview`   | Локальный просмотр прод-сборки      |
| `pnpm lint`      | ESLint                              |
| `pnpm typecheck` | Только проверка типов               |
| `pnpm format`    | Prettier                            |

## Структура (FSD)

```text
src/
  app/        — провайдеры (Query), роутер + гвард, layout-шелл, стили, mocks/
  pages/      — маршрутные слайсы: login, search, answer, not-found
  entities/   — бизнес-домены: query, session (api + model)
  shared/     — UI-кит, axios, api-error, конфиг, константы, типы
```

Маршруты за `RequireAuth`-гвардом (`app/router/guards/`) требуют JWT; без
токена — редирект на `/login`.

Импорты строго вниз по слоям: `app → pages → … → shared`. Каждый слайс
экспортируется через `index.ts` (публичный API). Подробности — в
[`docs/frontend/SKILL.md`](../docs/frontend/SKILL.md).

## Мок-бэкенд (MSW)

Пока реального бэкенда нет, запросы перехватывает [MSW](https://mswjs.io/) —
хендлеры в `src/app/mocks/`. Включён по умолчанию в dev; отключается
`VITE_ENABLE_MOCKS=false` (тогда запросы идут в реальный API через прокси).
Так реальные API-файлы (`entities/*/api/`) остаются тонкими и не знают о моках.

Замоканы:

- `POST /auth/login` — принимает любые email + пароль, отдаёт JWT + профиль
  (роль выводится из email: `admin@…`, `manager@…`, `expert@…`, иначе
  `researcher`).
- `GET /auth/me` — восстанавливает пользователя из bearer-токена.
- `POST /query` — структурированный ответ, реагирующий на выбранные фильтры.

## Контракт с бэкендом

Домен `entities/query` описывает `POST /query` (см.
[`docs/NLP_PIPELINE.md`](../docs/NLP_PIPELINE.md)): `QuerySpec` на входе,
структурированный ответ (`answer`, `consensus`, `disagreements`, `sources`,
`gaps`, `experts`, `subgraph`, `confidence`) на выходе. Домен `entities/session`
описывает `POST /auth/login` и `GET /auth/me`. JWT хранится в `localStorage` и
подставляется axios-интерсептором.

## Добавление shadcn-компонентов

```bash
pnpm dlx shadcn@latest add <component>
```

Компоненты кладутся в `src/shared/ui/` (алиасы — в `components.json`).
Экспортируйте их из `src/shared/ui/index.ts`.
