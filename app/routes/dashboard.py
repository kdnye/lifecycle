from flask import Blueprint, render_template

from services.dashboard import get_dashboard_metrics


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def index():
    metrics = get_dashboard_metrics()
    return render_template("dashboard/index.html", metrics=metrics)
