"""Backward-compatible module alias for Postmark email service.

Business logic is centralized in :mod:`app.services.email`.
"""

import sys

from app.services import email as _email

sys.modules[__name__] = _email
