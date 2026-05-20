from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash

from app.models import User, db


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: int
    email: str
    role: str | None
    can_manage_lifecycle: bool


def _safe_check_password(password_hash: str | None, raw_password: str) -> bool:
    if not password_hash:
        return False
    try:
        return check_password_hash(password_hash, raw_password)
    except (TypeError, ValueError):
        return False


def authenticate_user(email: str, raw_password: str) -> AuthenticatedPrincipal | None:
    """Authenticate against the shared users schema without assuming optional columns exist."""
    users_table = User.__table__
    inspector = inspect(db.engine)
    shared_columns = {col["name"] for col in inspector.get_columns(users_table.name)}

    required_columns = {"id", "email", "password_hash"}
    if not required_columns.issubset(shared_columns):
        return None

    selected_columns = [
        users_table.c.id,
        users_table.c.email,
        users_table.c.password_hash,
    ]
    has_role = "role" in shared_columns
    has_can_manage_lifecycle = "can_manage_lifecycle" in shared_columns
    if has_role:
        selected_columns.append(users_table.c.role)
    if has_can_manage_lifecycle:
        selected_columns.append(users_table.c.can_manage_lifecycle)

    row = db.session.execute(
        select(*selected_columns).where(users_table.c.email == email)
    ).mappings().first()

    if not row:
        return None

    if not _safe_check_password(row.get("password_hash"), raw_password):
        return None

    role = row.get("role")
    can_manage_lifecycle = bool(row.get("can_manage_lifecycle", False))
    if not has_can_manage_lifecycle and isinstance(role, str):
        can_manage_lifecycle = role.upper() in {"ADMIN", "SUPERADMIN", "IT_ADMIN"}

    return AuthenticatedPrincipal(
        user_id=int(row["id"]),
        email=str(row["email"]),
        role=role,
        can_manage_lifecycle=can_manage_lifecycle,
    )


def get_user_for_session(user_id: int) -> User | None:
    try:
        return db.session.get(User, user_id)
    except SQLAlchemyError:
        return None
