"""Backward-compatible module alias for lifecycle workflow service.

Business logic is centralized in :mod:`app.services.workflow`.
"""

import sys

from app.services import workflow as _workflow

sys.modules[__name__] = _workflow
