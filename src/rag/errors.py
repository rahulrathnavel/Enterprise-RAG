from __future__ import annotations


def compact_model_error(exc: Exception) -> str:
    """Return a UI-safe model error without stack traces or secrets."""

    status_code = getattr(exc, "status_code", None)
    if status_code:
        return f"{type(exc).__name__} from model provider, status {status_code}."
    return f"{type(exc).__name__}: {str(exc)[:220]}"


def is_transient_model_error(exc: Exception) -> bool:
    """Identify capacity/time-out errors that should degrade gracefully."""

    status_code = getattr(exc, "status_code", None)
    message = str(exc).lower()
    return (
        status_code in {408, 409, 429, 500, 502, 503, 504}
        or "resourceexhausted" in message
        or "all workers are busy" in message
        or "service unavailable" in message
        or "timeout" in message
        or "temporarily unavailable" in message
    )
