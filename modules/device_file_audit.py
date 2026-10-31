"""Consent-gated device manifest ingestion; does not receive file contents."""
import hashlib
import json
import re

from flask import Blueprint, current_app, jsonify, request

from .audit_log import record
from .db import connect
from .security import require_device_token
from .surveys import feature_enabled

bp = Blueprint("device_file_audit", __name__, url_prefix="/api/v1/device/file-audit")

MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 5000
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _error(code, status):
    return jsonify({"error": code, "content_received": False}), status


def _text(value, max_length, required=False):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if required and not value:
        return None
    if len(value) > max_length:
        return None
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return None
    return value


def _valid_relative_name(name):
    if not name or name.startswith("/") or "\\" in name:
        return False
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    return not any(ord(ch) < 32 or ord(ch) == 127 for ch in name)


@bp.post("/manifests")
@require_device_token
def receive_manifest():
    if not feature_enabled("file_transfer"):
        return _error("feature_disabled", 403)

    if request.content_length is not None and request.content_length > MAX_METADATA_BYTES:
        return _error("metadata_request_too_large", 413)

    if not request.is_json:
        return _error("json_required", 415)

    raw = request.get_json(silent=True)
    if not isinstance(raw, dict):
        return _error("json_object_required", 400)

    if raw.get("consent_granted") is not True:
        return _error("explicit_consent_required", 400)

    manifest_token = _text(raw.get("manifest_token"), 128, required=True)
    consent_version = _text(raw.get("consent_version"), 64, required=True)
    items = raw.get("items")

    if not manifest_token or not consent_version:
        return _error("invalid_manifest_identity_or_consent_version", 400)
    if not isinstance(items, list):
        return _error("items_array_required", 400)
    if len(items) > MAX_ITEMS:
        return jsonify({
            "error": "too_many_items",
            "max_items": MAX_ITEMS,
            "content_received": False,
        }), 413

    normalized = []
    total_size = 0
    seen_names = set()

    for item in items:
        if not isinstance(item, dict):
            return _error("invalid_item", 400)

        name = _text(item.get("relative_name"), 1024, required=True)
        size = item.get("size_bytes")
        mime = item.get("mime_type", "application/octet-stream")
        digest = item.get("sha256")
        modified = item.get("modified_at")

        if not name or not _valid_relative_name(name):
            return _error("unsafe_or_invalid_relative_name", 400)
        if name in seen_names:
            return _error("duplicate_relative_name", 400)
        seen_names.add(name)

        # bool is a subclass of int in Python; reject it explicitly.
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            return _error("invalid_size_bytes", 400)

        mime = _text(mime, 128, required=True)
        if not mime:
            return _error("invalid_mime_type", 400)

        if digest is not None:
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                return _error("invalid_sha256", 400)
            digest = digest.lower()

        if modified is not None:
            modified = _text(modified, 64, required=True)
            if not modified:
                return _error("invalid_modified_at", 400)

        total_size += size
        if total_size > 2**63 - 1:
            return _error("total_size_overflow", 400)

        normalized.append({
            "relative_name": name,
            "size_bytes": size,
            "mime_type": mime,
            "sha256": digest,
            "modified_at": modified,
        })

    # Stable canonical digest: computed by the server from normalized metadata.
    canonical = {
        "consent_version": consent_version,
        "items": normalized,
    }
    canonical_json = json.dumps(
        canonical, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )
    manifest_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    db = connect()
    try:
        # Serialize token check + insert to avoid concurrent duplicate manifests.
        db.execute("BEGIN IMMEDIATE")

        existing = db.execute(
            """SELECT m.id, m.device_id, m.manifest_sha256
               FROM file_audit_manifests m
               WHERE m.manifest_token=?""",
            (manifest_token,),
        ).fetchone()

        device = db.execute(
            "SELECT id FROM devices WHERE device_uid=? AND enabled=1",
            (request.device_uid,),
        ).fetchone()

        if device is None:
            db.rollback()
            return _error("device_not_found_or_disabled", 401)

        if existing is not None:
            if existing["device_id"] != device["id"]:
                db.rollback()
                return _error("manifest_token_conflict", 409)
            if existing["manifest_sha256"] != manifest_sha256:
                db.rollback()
                return _error("manifest_token_payload_conflict", 409)

            db.commit()
            return jsonify({
                "manifest_id": existing["id"],
                "status": "already_received",
                "item_count": len(normalized),
                "total_size_bytes": total_size,
                "manifest_sha256": manifest_sha256,
                "content_received": False,
            }), 200

        cur = db.execute(
            """INSERT INTO file_audit_manifests
               (device_id, manifest_token, consent_version, item_count,
                total_size_bytes, manifest_sha256)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                device["id"], manifest_token, consent_version,
                len(normalized), total_size, manifest_sha256,
            ),
        )
        manifest_id = cur.lastrowid

        for index, item in enumerate(normalized):
            # Internal item token is derived, not supplied as an access credential.
            item_identity = json.dumps(
                [index, item], ensure_ascii=False,
                sort_keys=True, separators=(",", ":"),
            )
            item_token = hashlib.sha256(
                item_identity.encode("utf-8")
            ).hexdigest()

            db.execute(
                """INSERT INTO file_audit_items
                   (manifest_id, item_token, relative_name, size_bytes,
                    mime_type, sha256, modified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    manifest_id, item_token, item["relative_name"],
                    item["size_bytes"], item["mime_type"],
                    item["sha256"], item["modified_at"],
                ),
            )

        db.commit()

    except Exception:
        db.rollback()
        current_app.logger.exception("Device manifest ingestion failed")
        return _error("manifest_ingestion_failed", 500)

    # Audit log stores counts only; no file contents or tokens.
    try:
        record(
            request.device_uid,
            "file_manifest_received",
            str(manifest_id),
            {"item_count": len(normalized), "total_size_bytes": total_size},
        )
    except Exception:
        current_app.logger.exception("Could not record manifest audit event")

    return jsonify({
        "manifest_id": manifest_id,
        "status": "received",
        "item_count": len(normalized),
        "total_size_bytes": total_size,
        "manifest_sha256": manifest_sha256,
        "content_received": False,
    }), 201
