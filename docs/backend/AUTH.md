# Auth & Users

## Роли

Определены в `domain/entities/user.py` (`UserRole`) согласно ТЗ:

- `admin` — управление пользователями, полный доступ
- `project_manager` — руководитель проекта
- `analyst` — аналитик
- `researcher` — исследователь
- `external_partner` — внешний партнёр (ограниченный доступ)

Публичной регистрации нет: пользователей заводит только админ через `POST /users`.

## Эндпоинты

| Метод | Путь            | Кто может        | Назначение                                                                   |
|-------|-----------------|------------------|------------------------------------------------------------------------------|
| POST  | `/auth/login`   | все              | JSON `{username, password}` → устанавливает `st_access` + `st_refresh` cookie |
| POST  | `/auth/refresh` | c refresh-cookie | Обновляет обе cookie                                                         |
| POST  | `/auth/logout`  | все              | Удаляет обе cookie                                                           |
| GET   | `/auth/me`      | authenticated    | Профиль текущего пользователя (auth по `st_access` cookie)                   |
| POST  | `/users`        | **admin**        | Создать пользователя                                                         |
| GET   | `/users`        | **admin**        | Список пользователей (`limit`, `offset`)                                     |

Все аутентифицированные ручки читают JWT из **cookie** `st_access` (`HttpOnly`,
`SameSite=lax`). Refresh-cookie ограничена path `/auth`. Тела ответов
`/auth/login` и `/auth/refresh` содержат только `access_expires_at` и
`refresh_expires_at` — сами токены наружу не отдаются.

Настройки cookie в `COOKIE_*` env: `COOKIE_SECURE=true` для HTTPS-продакшна,
`COOKIE_DOMAIN`, `COOKIE_SAMESITE`.

## Модель безопасности

- **Пароли**: argon2id (`passlib`). Инвариант raw-пароля: ≥8 символов, буквы+цифры.
- **Username**: 3–64 символа, нормализуется в lowercase.
- **Токены**: JWT HS256, раздельные типы `access` / `refresh`, `jti`, `iat`, `exp`, только через httpOnly-cookie.
- **RBAC**: FastAPI-зависимости `require_admin` / `require_roles(...)` из `features/shared/auth/`.
- **Ошибки**: единый envelope — `infrastructure/errors/handlers.py` + `ErrorResponse`.

## Формат ошибок

Все не-2xx ответы имеют одинаковую форму (`infrastructure/errors/schemas.py`):

```json
{ "message": "forbidden", "detail": ["requires one of: admin"] }
```

- `message` — короткий машиночитаемый код (`invalid_credentials`, `forbidden`,
  `weak_password`, `validation_error`, `user_exists`, ...).
- `detail` — опциональный список человекочитаемых уточнений. Отсутствует для
  ошибок без дополнительного контекста.

Валидация pydantic превращается в `{"message":"validation_error","detail":["body.password: String should have at least 8 characters", ...]}`.

## Сид админа (CLI)

`app/cli/seed_admin.py` — идемпотентная команда, читает `ADMIN_USERNAME` /
`ADMIN_PASSWORD` / `ADMIN_FULL_NAME` из окружения, любой параметр можно
переопределить флагом:

```
--username NAME            переопределить ADMIN_USERNAME
--password PASSWORD        переопределить ADMIN_PASSWORD
--full-name NAME           переопределить ADMIN_FULL_NAME
--reset-password           если админ уже есть — перезаписать пароль и активировать
```

Сид-команда специально **не применяет** инварианты `Username` / `RawPassword`,
чтобы можно было завести dev-креды типа `admin`/`admin`. Требования сложности
пароля действуют для всех остальных путей создания (в частности, `POST /users`).

## Что не сделано (следующие шаги)

- Alembic-миграции (сейчас `metadata.create_all` при старте)
- Ротация refresh-токенов + blacklist в БД
- Rate-limit на `/auth/login`
- Аудит-лог действий (требование ТЗ по управлению доступом)
- Самообслуживание: смена своего пароля, обновление профиля
- Деактивация/удаление пользователей через API
