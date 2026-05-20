"""Backward-compatible module alias for internal automation service.

Business logic is centralized in :mod:`app.services.internal_automation`.
"""

import sys

from app.services import internal_automation as _internal_automation

sys.modules[__name__] = _internal_automation
