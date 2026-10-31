import json
from flask import Blueprint, request, jsonify
from .db import connect
from .security import require_admin, require_device_token
from .surveys import feature_enabled
from .audit_log import record

bp = Blueprint("audit_requests", __name__, url_prefix="/api/v1")

@bp.post("/admin/audit-requests")
@require_admin
def create_request():
    data = request.get_json(silent=True) or {}
    uid = str(data.get("device_uid","")).strip()
    audit_type = data.get("audit_type","metadata")
    scope = data.get("scope",{})
    if not uid or audit_type not in ("metadata","content") or not isinstance(scope,dict):
        return jsonify({"error":"invalid_request"}), 400
    feature = "storage_audit" if audit_type == "metadata" else "content_audit"
    if not feature_enabled(feature):
        return jsonify({"error":"feature_disabled"}), 403
    if not connect().execute("SELECT 1 FROM devices WHERE device_uid=? AND enabled=1",(uid,)).fetchone():
        return jsonify({"error":"device_not_found"}), 404
    cur = connect().execute("INSERT INTO audit_requests(device_uid,audit_type,scope_json,requested_by) VALUES(?,?,?,?)",
                            (uid,audit_type,json.dumps(scope), "admin"))
    connect().commit()
    record("admin","audit_requested",str(cur.lastrowid),{"device_uid":uid,"audit_type":audit_type,"scope":scope})
    return jsonify({"request_id":cur.lastrowid,"status":"queued","notice":"The device must receive and display an audit notification before processing."}), 201

@bp.post("/device/heartbeat")
@require_device_token
def device_heartbeat():
    from flask import current_app
    db = connect()
    row = db.execute(
        "SELECT device_uid, last_seen, enabled FROM devices WHERE device_uid=?",
        (request.device_uid,),
    ).fetchone()
    if row is None or not row["enabled"]:
        return jsonify({"error": "device_not_found_or_disabled"}), 401

    timeout = int(current_app.config.get("DEVICE_OFFLINE_AFTER_SECONDS", 90))
    return jsonify({
        "device_uid": row["device_uid"],
        "status": "online",
        "last_seen": row["last_seen"],
        "offline_after_seconds": timeout,
    }), 200


@bp.get("/audit-requests/pending")
@require_device_token
def pending():
    rows = connect().execute("SELECT id,audit_type,scope_json,created_at FROM audit_requests WHERE device_uid=? AND status='queued' ORDER BY id",
                             (request.device_uid,)).fetchall()
    visible = []
    for r in rows:
        feature = "storage_audit" if r["audit_type"] == "metadata" else "content_audit"
        if not feature_enabled(feature):
            continue
        visible.append({
            "id": r["id"],
            "audit_type": r["audit_type"],
            "scope": json.loads(r["scope_json"]),
            "created_at": r["created_at"],
        })
    return jsonify(visible)

@bp.post("/audit-requests/<int:req_id>/result")
@require_device_token
def submit_result(req_id):
    data = request.get_json(silent=True) or {}
    db = connect()
    row = db.execute("SELECT * FROM audit_requests WHERE id=? AND device_uid=? AND status='queued'",
                     (req_id,request.device_uid)).fetchone()
    if not row:
        return jsonify({"error":"request_not_found"}), 404
    feature = "storage_audit" if row["audit_type"] == "metadata" else "content_audit"
    if not feature_enabled(feature):
        return jsonify({"error":"feature_disabled"}), 403

    result = data.get("result")
    if not isinstance(result, dict):
        return jsonify({"error":"result_object_required"}), 400

    try:
        result_json = json.dumps(result, ensure_ascii=False, allow_nan=False)
        result_size = len(result_json.encode("utf-8"))
    except (TypeError, ValueError):
        return jsonify({"error":"invalid_result_json"}), 400

    if result_size > 256 * 1024:
        return jsonify({"error":"result_too_large","max_bytes":256 * 1024}), 413

    db.execute("UPDATE audit_requests SET status='completed',completed_at=CURRENT_TIMESTAMP,result_json=? WHERE id=?",
               (result_json,req_id))
    db.commit()
    record(request.device_uid,"audit_result_received",str(req_id),{"result_keys":list(result.keys())})
    return jsonify({"status":"completed"})
