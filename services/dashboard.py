"""Dashboard service functions for lifecycle pipeline visibility."""

from sqlalchemy import func

from app.models import IntakeRequest, db


def get_dashboard_metrics() -> dict:
    """Return aggregate status counts and recent intake request activity."""
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
    }
