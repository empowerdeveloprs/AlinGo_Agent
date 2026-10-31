import hashlib, hmac, secrets
from functools import wraps
from flask import request, jsonify, session, redirect, url_for, flash
from werkzeug.security import check_password_hash

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def token_matches(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), stored_hash)

def require_admin(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_username"):
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)
    return wrapped

def require_device_token(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not token:
            return jsonify({"error":"bearer_token_required"}), 401
        from .db import connect
        db = connect()
        rows = db.execute("SELECT device_uid, token_hash FROM devices WHERE enabled=1").fetchall()
        for row in rows:
            if token_matches(token, row["token_hash"]):
                request.device_uid = row["device_uid"]
                db.execute("UPDATE devices SET last_seen=CURRENT_TIMESTAMP WHERE device_uid=?", (row["device_uid"],))
                db.commit()
                return fn(*args, **kwargs)
        return jsonify({"error":"invalid_or_revoked_token"}), 401
    return wrapped

def new_token():
    return secrets.token_urlsafe(32)
