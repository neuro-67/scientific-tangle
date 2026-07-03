"""Idempotent CLI: create (or update) the platform administrator.

Usage (from inside the backend container):

    docker compose exec backend python -m app.cli.seed_admin
    docker compose exec backend python -m app.cli.seed_admin \\
        --username admin --password 'S3cretPassphrase!' \\
        --full-name 'Anton V.'

CLI flags override ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_FULL_NAME from the
environment. Safe to run multiple times — existing admin is left untouched
unless --reset-password is passed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.domain.clock import now_utc
from app.domain.entities.user import UserRole
from app.domain.values.password import RawPassword
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.bootstrap import create_all
from app.infrastructure.database.engine import build_engine, build_session_factory
from app.infrastructure.database.tables.user import UserRow
from app.infrastructure.security.password_hasher import Argon2PasswordHasher


async def _run(
    *,
    reset_password: bool,
    username_override: str | None,
    password_override: str | None,
    full_name_override: str | None,
) -> int:
    settings = get_settings()
    seed = settings.admin_seed

    username_raw = username_override or seed.username
    password_raw = password_override or seed.password
    full_name = full_name_override or seed.full_name

    if not password_raw:
        print(
            "Password is not set. Pass --password or set ADMIN_PASSWORD in .env.",
            file=sys.stderr,
        )
        return 2

    # Seed CLI deliberately bypasses Username / RawPassword invariants so a dev
    # bootstrap like `admin`/`admin` works. Production paths (POST /users) keep
    # the invariants.
    username_value = username_raw.strip().lower()
    raw = _raw_password_unchecked(password_raw)

    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    hasher = Argon2PasswordHasher()

    try:
        await create_all(engine)

        async with session_factory() as session:
            existing = (
                await session.execute(select(UserRow).where(UserRow.username == username_value))
            ).scalar_one_or_none()

            if existing is None:
                now = now_utc()
                session.add(
                    UserRow(
                        id=_new_uuid(),
                        username=username_value,
                        hashed_password=hasher.hash(raw).value,
                        role=UserRole.ADMIN.value,
                        full_name=full_name,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
                await session.commit()
                print(f"admin created: {username_value}")
                return 0

            if reset_password:
                existing.hashed_password = hasher.hash(raw).value
                existing.role = UserRole.ADMIN.value
                existing.is_active = True
                existing.updated_at = now_utc()
                if full_name_override:
                    existing.full_name = full_name
                await session.commit()
                print(f"admin password reset: {username_value}")
                return 0

            print(f"admin already exists: {username_value} (use --reset-password to overwrite)")
            return 0
    finally:
        await engine.dispose()


def _raw_password_unchecked(value: str) -> RawPassword:
    obj = RawPassword.__new__(RawPassword)
    object.__setattr__(obj, "value", value)
    return obj


def _new_uuid():
    from uuid import uuid4

    return uuid4()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the platform administrator.")
    parser.add_argument("--username", help="Override ADMIN_USERNAME for this run.")
    parser.add_argument(
        "--password",
        help="Override ADMIN_PASSWORD for this run. Prefer stdin/env over shell history.",
    )
    parser.add_argument("--full-name", help="Override ADMIN_FULL_NAME for this run.")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="If the admin already exists, overwrite the password and reactivate.",
    )
    args = parser.parse_args()
    sys.exit(
        asyncio.run(
            _run(
                reset_password=args.reset_password,
                username_override=args.username,
                password_override=args.password,
                full_name_override=args.full_name,
            )
        )
    )


if __name__ == "__main__":
    main()
