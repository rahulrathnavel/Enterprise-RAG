from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "Admin"
    HR_FINANCE = "HR_Finance"
    ENGINEERING_OPS = "Engineering_Ops"


class AccessGroup(StrEnum):
    HR_FINANCE = "HR_FINANCE"
    ENGINEERING_OPS = "ENGINEERING_OPS"
    SHARED = "SHARED"


@dataclass(frozen=True)
class RolePolicy:
    role: Role
    allowed_source_types: tuple[str, ...]
    allowed_sql_tables: tuple[str, ...]
    allowed_classifications: tuple[str, ...]


ROLE_POLICIES: dict[Role, RolePolicy] = {
    Role.ADMIN: RolePolicy(
        role=Role.ADMIN,
        allowed_source_types=("pdf", "sql", "json_log"),
        allowed_sql_tables=("employees", "payroll", "infrastructure_assets", "incidents"),
        allowed_classifications=("public", "internal", "confidential", "restricted"),
    ),
    Role.HR_FINANCE: RolePolicy(
        role=Role.HR_FINANCE,
        allowed_source_types=("pdf", "sql"),
        allowed_sql_tables=("employees", "payroll"),
        allowed_classifications=("public", "internal", "confidential", "restricted"),
    ),
    Role.ENGINEERING_OPS: RolePolicy(
        role=Role.ENGINEERING_OPS,
        allowed_source_types=("pdf", "sql", "json_log"),
        allowed_sql_tables=("infrastructure_assets", "incidents"),
        allowed_classifications=("public", "internal"),
    ),
}


ACCESS_GROUP_ALLOWED_ROLES: dict[str, list[str]] = {
    AccessGroup.HR_FINANCE.value: [Role.ADMIN.value, Role.HR_FINANCE.value],
    AccessGroup.ENGINEERING_OPS.value: [Role.ADMIN.value, Role.ENGINEERING_OPS.value],
    AccessGroup.SHARED.value: [Role.ADMIN.value, Role.HR_FINANCE.value, Role.ENGINEERING_OPS.value],
}


def parse_role(value: str) -> Role:
    try:
        return Role(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported role: {value}") from exc


def get_policy(role: Role | str) -> RolePolicy:
    normalized = parse_role(role) if isinstance(role, str) else role
    return ROLE_POLICIES[normalized]


def allowed_roles_for_access_group(access_group: str) -> list[str]:
    return ACCESS_GROUP_ALLOWED_ROLES.get(access_group, [Role.ADMIN.value])


def can_access_source_type(role: Role | str, source_type: str) -> bool:
    return source_type in get_policy(role).allowed_source_types


def filter_route_for_role(role: Role | str, requested_sources: list[str]) -> list[str]:
    """Remove route targets that are not permitted for the active role."""

    policy = get_policy(role)
    return [source for source in requested_sources if source in policy.allowed_source_types]
