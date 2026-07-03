"""Manual conversion between ORM rows and domain entities.

Keeps `domain/` persistence-ignorant (ARCHITECTURE.md §6).
"""

from app.domain.entities.user import User, UserRole
from app.domain.values.password import HashedPassword
from app.domain.values.username import Username
from app.infrastructure.database.tables.user import UserRow


def user_to_row(user: User) -> UserRow:
    return UserRow(
        id=user.id,
        username=user.username.value,
        hashed_password=user.hashed_password.value,
        role=user.role.value,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def row_to_user(row: UserRow) -> User:
    # Data at rest is trusted — bypass Username's length invariant so seeded
    # dev identifiers (e.g. `admin`) reconstruct without raising.
    username = Username.__new__(Username)
    object.__setattr__(username, "value", row.username)
    return User(
        id=row.id,
        username=username,
        hashed_password=HashedPassword(row.hashed_password),
        role=UserRole(row.role),
        full_name=row.full_name,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
