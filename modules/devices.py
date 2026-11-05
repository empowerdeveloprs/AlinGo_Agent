from flask import Blueprint, request, jsonify
from .db import connect
from .security import require_admin, new_token, hash_token
from .audit_log import record

bp = Blueprint("devices", __name__, url_prefix="/devices")

@bp.get("")
@require_admin
def list_devices():
    timeout = int(__import__("flask").current_app.config.get("DEVICE_OFFLINE_AFTER_SECONDS", 90))
    rows = connect().execute(
        """
        SELECT device_uid, label, enabled, created_at, last_seen,
               CASE
                 WHEN enabled=1 AND last_seen IS NOT NULL
                  AND datetime(last_seen) >= datetime('now', ?)
                 THEN 'online'
                 ELSE 'offline'
               END AS connection_status
        FROM devices
        ORDER BY id DESC
        """,
        (f"-{timeout} seconds",),
    ).fetchall()
    return jsonify([dict(r) for r in rows])

@bp.post("")
@require_admin
def create_device():
    data = request.get_json(silent=True) or request.form
    uid = str(data.get("device_uid","")).strip()
    label = str(data.get("label","")).strip()
    if not uid:
        return jsonify({"error":"device_uid_required"}), 400
    token = new_token()
    db = connect()
    try:
        db.execute("INSERT INTO devices(device_uid,label,token_hash) VALUES(?,?,?)", (uid,label,hash_token(token)))
        db.commit()
    except Exception:
        return jsonify({"error":"device_uid_must_be_unique"}), 409
    record(session_actor(), "device_created", uid, {"label":label})
    # Token is shown only once. Store it securely on the device.
    return jsonify({"device_uid":uid,"label":label,"token_once":token}), 201

def session_actor():
    from flask import session
    return session.get("admin_username","admin")

@bp.get("/page")
@require_admin
def page():
    from flask import render_template
    return render_template("devices.html")
