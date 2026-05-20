"""Backward-compatible module alias for transactional mail wrapper.

Business logic is centralized in :mod:`app.services.mail`.
"""

import sys

from app.services import mail as _mail

sys.modules[__name__] = _mail
