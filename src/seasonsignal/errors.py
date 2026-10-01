"""User-facing errors raised by Season Signal."""

from __future__ import annotations


class PlanProblem(ValueError):
    """Raised when a moment, rule, campaign or lead time cannot be honoured as written."""


def friendly_message(exc: Exception) -> str:
    """Return a useful message without exposing an internal traceback by default."""
    if isinstance(exc, PlanProblem):
        return str(exc)
    if isinstance(exc, ValueError):
        return f"Season Signal could not complete that step: {exc}"
    return (
        "Season Signal could not complete that step. Check your inputs and try again. "
        "Set SEASONSIGNAL_DEBUG=1 before launch if you need technical details."
    )
