"""Backward-compatible module alias for intake dispatch service.

Business logic is centralized in :mod:`app.services.intake_dispatch`.
"""

import sys

from app.services import intake_dispatch as _intake_dispatch

sys.modules[__name__] = _intake_dispatch
