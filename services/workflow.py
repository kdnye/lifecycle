"""Backward-compatible proxy for lifecycle workflow service.

Business logic is centralized in :mod:`app.services.workflow`.
"""

from app.services import workflow as _workflow


def __getattr__(name: str):
    return getattr(_workflow, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_workflow)))
