"""Dashboard service functions for lifecycle pipeline visibility."""

import logging

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.models import IntakeRequest, db


logger = logging.getLogger(__name__)


def get_dashboard_metrics() -> dict:
    """Return aggregate status counts and recent intake request activity."""
    try:
        status_rows = (
            db.session.query(IntakeRequest.status, func.count(IntakeRequest.id))
            .group_by(IntakeRequest.status)
            .all()
        )

        status_counts = {status: count for status, count in status_rows}
        recent_activity = IntakeRequest.query.order_by(IntakeRequest.id.desc()).limit(10).all()

        return {
            "status_counts": status_counts,
            "recent_activity": recent_activity,
            "error": False,
        }
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.error("Dashboard metrics query failed: %s", exc)
        return {
            "status_counts": {},
            "recent_activity": [],
            "error": True,
        }
