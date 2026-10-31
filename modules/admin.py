from flask import Blueprint, request, jsonify
from .db import connect
from .security import require_admin
from .audit_log import record

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.post("/devices/<device_uid>/connection")
@require_admin
def set_device_connection(device_uid):
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        return jsonify({"error": "enabled_boolean_required"}), 400

    db = connect()
    row = db.execute(
        "SELECT device_uid, enabled FROM devices WHERE device_uid=?",
        (device_uid,),
    ).fetchone()
    if row is None:
        return jsonify({"error": "device_not_found"}), 404

    db.execute(
        "UPDATE devices SET enabled=? WHERE device_uid=?",
        (int(enabled), device_uid),
    )

    cancelled = 0
    if not enabled:
        cur = db.execute(
            "UPDATE audit_requests SET status='cancelled' "
            "WHERE device_uid=? AND status='queued'",
            (device_uid,),
        )
        cancelled = cur.rowcount

    db.commit()
    record(
        "admin",
        "device_connection_changed",
        device_uid,
        {"enabled": enabled, "cancelled_requests": cancelled},
    )
    return jsonify({
        "device_uid": device_uid,
        "enabled": enabled,
        "cancelled_requests": cancelled,
    }), 200

@bp.get("/features")
@require_admin
def list_features():
    return jsonify([dict(r) for r in connect().execute("SELECT name,enabled FROM feature_flags ORDER BY name")])

@bp.post("/features/<name>")
@require_admin
def toggle_feature(name):
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("enabled"), bool):
        return jsonify({"error":"enabled_boolean_required"}), 400
    db = connect()
    if not db.execute("SELECT 1 FROM feature_flags WHERE name=?",(name,)).fetchone():
        return jsonify({"error":"unknown_feature"}), 404
    db.execute("UPDATE feature_flags SET enabled=? WHERE name=?",(int(data["enabled"]),name))
    db.commit()
    record("admin","feature_toggled",name,{"enabled":data["enabled"]})
    return jsonify({"name":name,"enabled":data["enabled"]})
