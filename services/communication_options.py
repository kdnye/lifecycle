"""Backward-compatible module alias for communication options service.

Business logic is centralized in :mod:`app.services.communication_options`.
"""

import sys

from app.services import communication_options as _communication_options

sys.modules[__name__] = _communication_options
