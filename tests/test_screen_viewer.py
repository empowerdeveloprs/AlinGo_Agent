import os
import sqlite3
import tempfile
import unittest

from app import create_app
from modules.security import hash_token


class ScreenViewerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "screen-viewer.db")
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "screen-viewer-test-secret",
            "DATABASE_PATH": self.db_path,
        })
        self.client = self.app.test_client()
        self.token_a = "test-device-token-A"
        self.token_b = "test-device-token-B"
        self.add_device("device-A", self.token_a)
        self.add_device("device-B", self.token_b)

    def tearDown(self):
        self.tmp.cleanup()

    def db(self):
        return sqlite3.connect(self.db_path)

    def add_device(self, uid, token):
        db = self.db()
        try:
            db.execute(
                """
                INSERT INTO devices(device_uid, label, token_hash)
                VALUES (?, ?, ?)
                """,
                (uid, uid, hash_token(token)),
            )
            db.commit()
        finally:
            db.close()

    def admin_login(self):
        with self.client.session_transaction() as session:
            session["admin_username"] = "test-admin"

    def enable_feature(self, enabled=True):
        db = self.db()
        try:
            db.execute(
                "UPDATE feature_flags SET enabled=? WHERE name='screen_viewer'",
                (int(enabled),),
            )
            db.commit()
        finally:
            db.close()

    def request_session(self, uid="device-A", duration=120):
        self.admin_login()
        return self.client.post(
            "/admin/screen-viewer/sessions",
            json={
                "device_uid": uid,
                "duration_seconds": duration,
            },
        )

    def device_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_feature_disabled_rejects_admin_and_device_requests(self):
        self.assertEqual(
            self.client.post(
                "/admin/screen-viewer/sessions",
                json={"device_uid": "device-A"},
            ).status_code,
            302,
        )
        self.admin_login()
        response = self.client.post(
            "/admin/screen-viewer/sessions",
            json={"device_uid": "device-A"},
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.get(
            "/api/v1/screen-viewer/pending",
            headers=self.device_headers(self.token_a),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_session_for_enabled_device(self):
        self.enable_feature()
        response = self.request_session()
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["status"], "requested")
        self.assertIn("session_id", data)

    def test_unknown_device_is_rejected(self):
        self.enable_feature()
        response = self.request_session("missing-device")
        self.assertEqual(response.status_code, 404)

    def test_invalid_session_duration_is_rejected(self):
        self.enable_feature()
        for duration in (0, 301, True, "120"):
            with self.subTest(duration=duration):
                response = self.request_session(duration=duration)
                self.assertEqual(response.status_code, 400)

    def test_only_assigned_device_can_approve_session(self):
        self.enable_feature()
        response = self.request_session()
        session_id = response.get_json()["session_id"]

        response = self.client.post(
            f"/api/v1/screen-viewer/sessions/{session_id}/consent",
            json={
                "decision": "approve",
                "consent_version": "screen-viewer-v1",
            },
            headers=self.device_headers(self.token_b),
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            f"/api/v1/screen-viewer/sessions/{session_id}/consent",
            json={
                "decision": "approve",
                "consent_version": "screen-viewer-v1",
            },
            headers=self.device_headers(self.token_a),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "approved")

    def test_approval_requires_expected_consent_version(self):
        self.enable_feature()
        session_id = self.request_session().get_json()["session_id"]

        response = self.client.post(
            f"/api/v1/screen-viewer/sessions/{session_id}/consent",
            json={"decision": "approve", "consent_version": "wrong-version"},
            headers=self.device_headers(self.token_a),
        )
        self.assertEqual(response.status_code, 400)

    def test_device_can_deny_request(self):
        self.enable_feature()
        session_id = self.request_session().get_json()["session_id"]

        response = self.client.post(
            f"/api/v1/screen-viewer/sessions/{session_id}/consent",
            json={"decision": "deny"},
            headers=self.device_headers(self.token_a),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "denied")

    def test_admin_can_stop_approved_session(self):
        self.enable_feature()
        session_id = self.request_session().get_json()["session_id"]

        self.client.post(
            f"/api/v1/screen-viewer/sessions/{session_id}/consent",
            json={
                "decision": "approve",
                "consent_version": "screen-viewer-v1",
            },
            headers=self.device_headers(self.token_a),
        )

        self.admin_login()
        response = self.client.post(
            f"/admin/screen-viewer/sessions/{session_id}/stop"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ended")

    def test_device_can_stop_own_approved_session(self):
        self.enable_feature()
        session_id = self.request_session().get_json()["session_id"]

        self.client.post(
            f"/api/v1/screen-viewer/sessions/{session_id}/consent",
            json={
                "decision": "approve",
                "consent_version": "screen-viewer-v1",
            },
            headers=self.device_headers(self.token_a),
        )

        response = self.client.post(
            f"/api/v1/screen-viewer/sessions/{session_id}/stop",
            headers=self.device_headers(self.token_a),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ended")


if __name__ == "__main__":
    unittest.main()

    def test_expired_request_cannot_be_approved(self):
        self.enable_feature()
        session_id = self.request_session().get_json()["session_id"]

        db = self.db()
        try:
            db.execute(
                """
                UPDATE screen_viewer_sessions
                SET expires_at='2000-01-01 00:00:00'
                WHERE id=?
                """,
                (session_id,),
            )
            db.commit()
        finally:
            db.close()

        response = self.client.post(
            f"/api/v1/screen-viewer/sessions/{session_id}/consent",
            json={
                "decision": "approve",
                "consent_version": "screen-viewer-v1",
            },
            headers=self.device_headers(self.token_a),
        )

        self.assertEqual(response.status_code, 404)

        db = self.db()
        try:
            row = db.execute(
                "SELECT status FROM screen_viewer_sessions WHERE id=?",
                (session_id,),
            ).fetchone()
            self.assertEqual(row[0], "expired")
        finally:
            db.close()
