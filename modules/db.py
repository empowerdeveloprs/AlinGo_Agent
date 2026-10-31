import os, sqlite3
from pathlib import Path
from flask import current_app, g

SCHEMA = '''
CREATE TABLE IF NOT EXISTS admins (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS devices (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 device_uid TEXT UNIQUE NOT NULL,
 label TEXT NOT NULL DEFAULT '',
 token_hash TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 last_seen TEXT
);
CREATE TABLE IF NOT EXISTS surveys (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 schema_json TEXT NOT NULL DEFAULT '[]',
 enabled INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS survey_responses (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 survey_id INTEGER NOT NULL REFERENCES surveys(id),
 device_uid TEXT NOT NULL,
 response_json TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_requests (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 device_uid TEXT NOT NULL,
 audit_type TEXT NOT NULL CHECK(audit_type IN ('metadata','content')),
 scope_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'queued',
 requested_by TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 completed_at TEXT,
 result_json TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 actor TEXT NOT NULL,
 action TEXT NOT NULL,
 target TEXT NOT NULL DEFAULT '',
 details_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidate_links (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 candidate_label TEXT NOT NULL,
 token_hash TEXT UNIQUE NOT NULL,
 expires_at TEXT NOT NULL,
 revoked INTEGER NOT NULL DEFAULT 0,
 consented_at TEXT,
 consent_version TEXT,
 permission_report_json TEXT,
 survey_json TEXT,
 created_by TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS file_audit_manifests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    manifest_token TEXT NOT NULL UNIQUE,
    consent_version TEXT NOT NULL,
    item_count INTEGER NOT NULL DEFAULT 0 CHECK(item_count >= 0),
    total_size_bytes INTEGER NOT NULL DEFAULT 0 CHECK(total_size_bytes >= 0),
    manifest_sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'received'
        CHECK(status IN ('received', 'reviewed', 'expired', 'revoked')),
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(device_id) REFERENCES devices(id)
);

CREATE INDEX IF NOT EXISTS idx_file_audit_manifests_device
    ON file_audit_manifests(device_id, received_at);

CREATE TABLE IF NOT EXISTS file_audit_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manifest_id INTEGER NOT NULL,
    item_token TEXT NOT NULL,
    relative_name TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    sha256 TEXT,
    modified_at TEXT,
    transfer_status TEXT NOT NULL DEFAULT 'metadata_only'
        CHECK(transfer_status IN (
            'metadata_only', 'queued', 'uploading',
            'complete', 'failed', 'cancelled'
        )),
    transferred_bytes INTEGER NOT NULL DEFAULT 0
        CHECK(transferred_bytes >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(manifest_id, item_token),
    FOREIGN KEY(manifest_id) REFERENCES file_audit_manifests(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_file_audit_items_manifest
    ON file_audit_items(manifest_id, id);

CREATE TABLE IF NOT EXISTS file_transfers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 item_id INTEGER NOT NULL UNIQUE
     REFERENCES file_audit_items(id),
 device_id INTEGER NOT NULL
     REFERENCES devices(id),
 status TEXT NOT NULL DEFAULT 'pending'
     CHECK(status IN (
         'pending', 'awaiting_device_consent', 'approved',
         'uploading', 'verifying', 'complete',
         'failed', 'cancelled'
     )),
 expected_size_bytes INTEGER NOT NULL
     CHECK(expected_size_bytes >= 0),
 received_bytes INTEGER NOT NULL DEFAULT 0
     CHECK(received_bytes >= 0 AND received_bytes <= expected_size_bytes),
 expected_sha256 TEXT,
 verified_sha256 TEXT,
 storage_key TEXT NOT NULL UNIQUE,
 consent_version TEXT,
 consented_at TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_file_transfers_device_status
 ON file_transfers(device_id, status, id);

CREATE TABLE IF NOT EXISTS feature_flags (
 name TEXT PRIMARY KEY,
 enabled INTEGER NOT NULL DEFAULT 1
);
'''

def connect():
    if "db" not in g:
        path = Path(current_app.config["DATABASE_PATH"])
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def init_db():
    db = connect()
    db.executescript(SCHEMA)
    for name in ("surveys", "storage_audit", "content_audit", "file_transfer"):
        db.execute("INSERT OR IGNORE INTO feature_flags(name, enabled) VALUES(?,1)", (name,))
    db.commit()

def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
