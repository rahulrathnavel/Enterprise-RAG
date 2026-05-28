from src.rag.errors import is_transient_model_error
from src.rag.router import AgenticRouter
from src.security.rbac import Role


class BusyModelError(Exception):
    status_code = 503


def test_transient_model_error_detection() -> None:
    assert is_transient_model_error(BusyModelError("All workers are busy"))
    assert is_transient_model_error(Exception("Request timed out."))


def test_router_degrades_to_rbac_safe_heuristic_on_capacity_error() -> None:
    router = AgenticRouter.__new__(AgenticRouter)
    router.client = object()
    router._remote_route = lambda query, role: (_ for _ in ()).throw(BusyModelError("ResourceExhausted"))
    router._heuristic_route = lambda query: ["sql", "json_log"]

    decision = router.route("show incident logs", Role.HR_FINANCE)

    assert decision.source_types == ["sql"]
    assert decision.denied_source_types == ["json_log"]
    assert "deterministic RBAC-safe route" in decision.rationale
