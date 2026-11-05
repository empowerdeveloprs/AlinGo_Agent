"""File-audit foundation for Zentrix Device Connect.

This module deliberately does not scan device storage or transfer file contents.
File discovery and content transfer require explicit device-side consent.
"""
from flask import Blueprint, jsonify, render_template
from .security import require_admin
from .surveys import feature_enabled

bp = Blueprint("file_audit", __name__, url_prefix="/admin/file-audit")


@bp.get("/status")
@require_admin
def status():
    """Report whether the file-transfer feature is enabled."""
    enabled = feature_enabled("file_transfer")
    return jsonify({
        "feature": "file_transfer",
        "enabled": enabled,
        "content_transfer_implemented": False,
        "notice": (
            "No device files are scanned or transferred by this endpoint."
        ),
    }), 200

@bp.get("/manifests")
@require_admin
def list_manifests():
    """List manifest metadata without exposing internal tokens or file contents."""
    from flask import request
    from .db import connect

    if not feature_enabled("file_transfer"):
        return jsonify({
            "enabled": False,
            "manifests": [],
            "count": 0,
            "content_transferred_by_this_endpoint": False,
        }), 200

    db = connect()
    device_uid = request.args.get("device_uid", "").strip()

    try:
        limit = int(request.args.get("limit", "50"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_limit"}), 400

    if not 1 <= limit <= 100:
        return jsonify({
            "error": "limit_out_of_range",
            "allowed": "1-100",
        }), 400

    # Limit manifests first, not joined item rows.
    sql = """
        SELECT
            m.id AS manifest_id,
            d.device_uid,
            d.label AS device_label,
            m.consent_version,
            m.item_count,
            m.total_size_bytes,
            m.manifest_sha256,
            m.status AS manifest_status,
            m.received_at
        FROM file_audit_manifests AS m
        JOIN devices AS d ON d.id = m.device_id
    """
    params = []

    if device_uid:
        sql += " WHERE d.device_uid = ?"
        params.append(device_uid)

    sql += " ORDER BY m.received_at DESC, m.id DESC LIMIT ?"
    params.append(limit)

    manifest_rows = db.execute(sql, params).fetchall()
    manifests = []

    for row in manifest_rows:
        manifest_id = row["manifest_id"]
        item_rows = db.execute(
            """
            SELECT
                id AS item_id,
                relative_name,
                size_bytes,
                mime_type,
                sha256,
                modified_at,
                transfer_status,
                transferred_bytes
            FROM file_audit_items
            WHERE manifest_id = ?
            ORDER BY id ASC
            """,
            (manifest_id,),
        ).fetchall()

        manifests.append({
            "manifest_id": manifest_id,
            "device_uid": row["device_uid"],
            "device_label": row["device_label"],
            "consent_version": row["consent_version"],
            "item_count": row["item_count"],
            "total_size_bytes": row["total_size_bytes"],
            "manifest_sha256": row["manifest_sha256"],
            "status": row["manifest_status"],
            "received_at": row["received_at"],
            "items": [
                {
                    "item_id": item["item_id"],
                    "relative_name": item["relative_name"],
                    "size_bytes": item["size_bytes"],
                    "mime_type": item["mime_type"],
                    "sha256": item["sha256"],
                    "modified_at": item["modified_at"],
                    "transfer_status": item["transfer_status"],
                    "transferred_bytes": item["transferred_bytes"],
                }
                for item in item_rows
            ],
        })

    return jsonify({
        "enabled": True,
        "manifests": manifests,
        "count": len(manifests),
        "content_transferred_by_this_endpoint": False,
    }), 200






@bp.post("/transfers")
@require_admin
def request_transfer():
    """Queue one selected manifest item directly with valid pending status."""
    import secrets
    from flask import request
    from .db import connect
    from .audit_log import record

    if not feature_enabled("file_transfer"):
        return jsonify({"error": "feature_disabled"}), 403

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "json_object_required"}), 400

    item_id = payload.get("item_id")
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id <= 0:
        return jsonify({"error": "valid_item_id_required"}), 400

    db = connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        item = db.execute(
            """
            SELECT i.id AS item_id, i.manifest_id, i.size_bytes, i.sha256,
                   i.transfer_status, m.device_id, m.status AS manifest_status,
                   d.device_uid, d.enabled AS device_enabled
            FROM file_audit_items i
            JOIN file_audit_manifests m ON m.id = i.manifest_id
            JOIN devices d ON d.id = m.device_id
            WHERE i.id = ?
            """,
            (item_id,),
        ).fetchone()

        if item is None:
            db.rollback()
            return jsonify({"error": "item_not_found"}), 404
        if not item["device_enabled"]:
            db.rollback()
            return jsonify({"error": "device_disabled"}), 409

        existing = db.execute(
            "SELECT id, status FROM file_transfers WHERE item_id = ?",
            (item_id,),
        ).fetchone()
        if existing is not None:
            db.commit()
            return jsonify({
                "transfer_id": existing["id"],
                "status": existing["status"],
                "already_requested": True,
                "content_received": False,
            }), 200

        storage_key = secrets.token_hex(32)
        cur = db.execute(
            """
            INSERT INTO file_transfers
                (item_id, device_id, status, expected_size_bytes,
                 received_bytes, expected_sha256, storage_key)
            VALUES (?, ?, 'pending', ?, 0, ?, ?)
            """,
            (
                item["item_id"],
                item["device_id"],
                item["size_bytes"],
                item["sha256"],
                storage_key,
            ),
        )
        transfer_id = cur.lastrowid
        db.commit()
    except Exception:
        db.rollback()
        raise

    try:
        record(
            "admin",
            "file_transfer_requested",
            str(transfer_id),
            {"item_id": item_id, "device_uid": item["device_uid"]},
        )
    except Exception:
        pass

    return jsonify({
        "transfer_id": transfer_id,
        "item_id": item_id,
        "device_uid": item["device_uid"],
        "status": "pending",
        "expected_size_bytes": item["size_bytes"],
        "content_received": False,
    }), 201

@bp.get("/page")
@require_admin
def page():
    return render_template("file_audit.html")
