import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, render_template

from .db import connect
from .security import require_admin, require_device_token
from .surveys import feature_enabled
from .audit_log import record


admin_bp = Blueprint(
    "screen_viewer_admin",
    __name__,
    url_prefix="/admin/screen-viewer",
)

device_bp = Blueprint(
    "screen_viewer_device",
    __name__,
    url_prefix="/api/v1/screen-viewer",
)

CONSENT_VERSION = "screen-viewer-v1"
MIN_DURATION = 30
MAX_DURATION = 300


def feature_required():
    if not feature_enabled("screen_viewer"):
        return jsonify({"error": "feature_disabled"}), 403
    return None


def expire_pending(db, device_uid=None):
    if device_uid is None:
        db.execute(
            """
            UPDATE screen_viewer_sessions
            SET status='expired', ended_at=CURRENT_TIMESTAMP,
                end_reason='request_timeout'
            WHERE status IN ('requested','approved') AND expires_at <= CURRENT_TIMESTAMP
            """
        )
    else:
        db.execute(
            """
            UPDATE screen_viewer_sessions
            SET status='expired', ended_at=CURRENT_TIMESTAMP,
                end_reason='request_timeout'
            WHERE device_id=(
                SELECT id FROM devices WHERE device_uid=?
            )
            AND status IN ('requested','approved') AND expires_at <= CURRENT_TIMESTAMP
            """,
            (device_uid,),
        )
    db.commit()


@admin_bp.post("/sessions")
@require_admin
def create_session():
    disabled = feature_required()
    if disabled:
        return disabled

    data = request.get_json(silent=True) or {}
    uid = data.get("device_uid")
    if not isinstance(uid, str) or not uid.strip():
        return jsonify({"error": "device_uid_required"}), 400

    duration = data.get("duration_seconds", 120)
    if (
        isinstance(duration, bool)
        or not isinstance(duration, int)
        or not MIN_DURATION <= duration <= MAX_DURATION
    ):
        return jsonify({
            "error": "invalid_duration",
            "minimum_seconds": MIN_DURATION,
            "maximum_seconds": MAX_DURATION,
        }), 400

    db = connect()
    device = db.execute(
        "SELECT id FROM devices WHERE device_uid=? AND enabled=1",
        (uid.strip(),),
    ).fetchone()

    if not device:
        return jsonify({"error": "device_not_found"}), 404

    expire_pending(db)
    cur = db.execute(
        """
        INSERT INTO screen_viewer_sessions
            (device_id, requested_by, expires_at)
        VALUES (?, ?, datetime('now', ?))
        """,
        (device["id"], "admin", f"+{duration} seconds"),
    )
    db.commit()

    session_id = cur.lastrowid
    record(
        "admin",
        "screen_view_requested",
        str(session_id),
        {"device_uid": uid.strip(), "duration_seconds": duration},
    )

    return jsonify({
        "session_id": session_id,
        "status": "requested",
        "duration_seconds": duration,
        "notice": (
            "The device must show a clear consent prompt. "
            "No screen content is captured by this endpoint."
        ),
    }), 201


@admin_bp.get("/sessions")
@require_admin
def list_sessions():
    disabled = feature_required()
    if disabled:
        return disabled

    db = connect()
    expire_pending(db)

    rows = db.execute(
        """
        SELECT s.id, d.device_uid, s.requested_by, s.status,
               s.consent_version, s.consented_at, s.requested_at,
               s.expires_at, s.ended_at, s.end_reason
        FROM screen_viewer_sessions s
        JOIN devices d ON d.id=s.device_id
        ORDER BY s.id DESC LIMIT 100
        """
    ).fetchall()

    return jsonify([dict(row) for row in rows])


@admin_bp.post("/sessions/<int:session_id>/stop")
@require_admin
def admin_stop_session(session_id):
    disabled = feature_required()
    if disabled:
        return disabled

    db = connect()
    row = db.execute(
        "SELECT status FROM screen_viewer_sessions WHERE id=?",
        (session_id,),
    ).fetchone()

    if not row:
        return jsonify({"error": "session_not_found"}), 404

    if row["status"] not in ("requested", "approved"):
        return jsonify({"error": "session_not_active"}), 409

    new_status = "cancelled" if row["status"] == "requested" else "ended"
    db.execute(
        """
        UPDATE screen_viewer_sessions
        SET status=?, ended_at=CURRENT_TIMESTAMP, end_reason='admin_stopped'
        WHERE id=?
        """,
        (new_status, session_id),
    )
    db.commit()

    record("admin", "screen_view_stopped", str(session_id), {
        "status": new_status,
    })
    return jsonify({"session_id": session_id, "status": new_status})


@device_bp.get("/pending")
@require_device_token
def device_pending():
    disabled = feature_required()
    if disabled:
        return disabled

    db = connect()
    expire_pending(db, request.device_uid)

    rows = db.execute(
        """
        SELECT s.id, s.requested_at, s.expires_at
        FROM screen_viewer_sessions s
        JOIN devices d ON d.id=s.device_id
        WHERE d.device_uid=? AND s.status='requested'
          AND s.expires_at > CURRENT_TIMESTAMP
        ORDER BY s.id
        """,
        (request.device_uid,),
    ).fetchall()

    return jsonify([dict(row) for row in rows])


@device_bp.post("/sessions/<int:session_id>/consent")
@require_device_token
def device_consent(session_id):
    disabled = feature_required()
    if disabled:
        return disabled

    data = request.get_json(silent=True) or {}
    decision = data.get("decision")

    if decision not in ("approve", "deny"):
        return jsonify({"error": "decision_must_be_approve_or_deny"}), 400

    if decision == "approve" and data.get("consent_version") != CONSENT_VERSION:
        return jsonify({"error": "valid_consent_version_required"}), 400

    db = connect()
    expire_pending(db, request.device_uid)

    row = db.execute(
        """
        SELECT s.id, s.status
        FROM screen_viewer_sessions s
        JOIN devices d ON d.id=s.device_id
        WHERE s.id=? AND d.device_uid=?
        """,
        (session_id, request.device_uid),
    ).fetchone()

    if not row or row["status"] != "requested":
        return jsonify({"error": "pending_session_not_found"}), 404

    if decision == "approve":
        db.execute(
            """
            UPDATE screen_viewer_sessions
            SET status='approved', consent_version=?,
                consented_at=CURRENT_TIMESTAMP
            WHERE id=? AND status='requested'
            """,
            (CONSENT_VERSION, session_id),
        )
        status = "approved"
    else:
        db.execute(
            """
            UPDATE screen_viewer_sessions
            SET status='denied', ended_at=CURRENT_TIMESTAMP,
                end_reason='device_user_denied'
            WHERE id=? AND status='requested'
            """,
            (session_id,),
        )
        status = "denied"

    db.commit()
    record(
        request.device_uid,
        "screen_view_consent",
        str(session_id),
        {"decision": decision},
    )

    return jsonify({"session_id": session_id, "status": status})


@device_bp.post("/sessions/<int:session_id>/stop")
@require_device_token
def device_stop_session(session_id):
    disabled = feature_required()
    if disabled:
        return disabled

    db = connect()
    row = db.execute(
        """
        SELECT s.status
        FROM screen_viewer_sessions s
        JOIN devices d ON d.id=s.device_id
        WHERE s.id=? AND d.device_uid=?
        """,
        (session_id, request.device_uid),
    ).fetchone()

    if not row or row["status"] != "approved":
        return jsonify({"error": "active_session_not_found"}), 404

    db.execute(
        """
        UPDATE screen_viewer_sessions
        SET status='ended', ended_at=CURRENT_TIMESTAMP,
            end_reason='device_user_stopped'
        WHERE id=? AND status='approved'
        """,
        (session_id,),
    )
    db.commit()

    record(
        request.device_uid,
        "screen_view_stopped",
        str(session_id),
        {"reason": "device_user_stopped"},
    )
    return jsonify({"session_id": session_id, "status": "ended"})

@admin_bp.get("/page")
@require_admin
def page():
    return render_template("screen_viewer.html")
