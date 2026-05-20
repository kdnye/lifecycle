"""Backward-compatible module alias for dashboard service.

Business logic is centralized in :mod:`app.services.dashboard`.
"""

import sys

from app.services import dashboard as _dashboard

sys.modules[__name__] = _dashboard
