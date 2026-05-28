from src.security.rbac import Role, allowed_roles_for_access_group, filter_route_for_role, get_policy


def test_hr_finance_is_blocked_from_json_logs() -> None:
    filtered = filter_route_for_role(Role.HR_FINANCE, ["pdf", "sql", "json_log"])
    assert filtered == ["pdf", "sql"]


def test_engineering_ops_tables_exclude_payroll() -> None:
    policy = get_policy(Role.ENGINEERING_OPS)
    assert "infrastructure_assets" in policy.allowed_sql_tables
    assert "incidents" in policy.allowed_sql_tables
    assert "payroll" not in policy.allowed_sql_tables


def test_access_group_allowed_roles() -> None:
    assert allowed_roles_for_access_group("HR_FINANCE") == ["Admin", "HR_Finance"]
    assert allowed_roles_for_access_group("ENGINEERING_OPS") == ["Admin", "Engineering_Ops"]
