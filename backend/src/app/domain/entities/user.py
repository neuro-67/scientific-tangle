"""User aggregate and role enum."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.entities.base import BaseEntity
from app.domain.values.password import HashedPassword
from app.domain.values.username import Username


class UserRole(StrEnum):
    """Roles defined by the R&D knowledge platform brief."""

    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    ANALYST = "analyst"
    RESEARCHER = "researcher"
    EXTERNAL_PARTNER = "external_partner"


@dataclass(kw_only=True)
class User(BaseEntity):
    """Authenticated principal with a role and hashed credentials."""

    username: Username
    hashed_password: HashedPassword
    role: UserRole
    full_name: str
    is_active: bool = True

    @classmethod
    def create(
        cls,
        *,
        username: Username,
        hashed_password: HashedPassword,
        role: UserRole,
        full_name: str,
    ) -> User:
        return cls(
            username=username,
            hashed_password=hashed_password,
            role=role,
            full_name=full_name.strip(),
        )

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def change_password(self, new_hash: HashedPassword) -> None:
        self.hashed_password = new_hash
        self.touch()

    def can_manage_users(self) -> bool:
        return self.role is UserRole.ADMIN
