from flask import Blueprint, render_template
from .security import require_admin
from .db import connect

bp = Blueprint("dashboard", __name__)


@bp.get("/")
@require_admin
def dashboard():
    return render_template("dashboard.html")


@bp.get("/api/dashboard-summary")
@require_admin
def dashboard_summary():
    db = connect()
    counts = {}
    for table in (
        "devices",
        "surveys",
        "survey_responses",
        "audit_requests",
        "audit_events",
    ):
        counts[table] = db.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
    return {"app": "Zentrix Device Connect", "counts": counts}
