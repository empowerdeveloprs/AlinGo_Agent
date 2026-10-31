import os
import sqlite3
import tempfile
import unittest

from app import create_app


class DeviceAuditContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "isolated-test.db")

        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "isolated-test-secret",
            "DATABASE_PATH": self.db_path,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def admin_login(self):
        # صرف ٹیسٹ کلائنٹ کی سیشن؛ اصل منتظم یا پاس ورڈ تبدیل نہیں ہوتا۔
        with self.client.session_transaction() as sess:
            sess["admin_username"] = "test-admin"

    def create_device(self, uid):
        self.admin_login()
        response = self.client.post(
            "/devices",
            json={"device_uid": uid, "label": "Automated test device"},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        data = response.get_json()
        self.assertEqual(data["device_uid"], uid)
        self.assertIn("token_once", data)
        return data["token_once"]

    def device_get(self, path, token):
        return self.client.get(
            path,
            headers={"Authorization": f"Bearer {token}"},
        )

    def device_post(self, path, token, payload):
        return self.client.post(
            path,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    def create_audit_request(self, uid, audit_type="metadata", scope=None):
        self.admin_login()
        return self.client.post(
            "/api/v1/admin/audit-requests",
            json={
                "device_uid": uid,
                "audit_type": audit_type,
                "scope": scope or {"mode": "metadata_only"},
            },
        )

    def test_device_registration_returns_token_once_and_stores_hash(self):
        token = self.create_device("test-device-01")
        self.assertTrue(token)

        db = sqlite3.connect(self.db_path)
        try:
            row = db.execute(
                "SELECT token_hash FROM devices WHERE device_uid=?",
                ("test-device-01",),
            ).fetchone()
        finally:
            db.close()

        self.assertIsNotNone(row)
        self.assertNotEqual(row[0], token)

    def test_duplicate_device_uid_is_rejected(self):
        self.create_device("duplicate-device")

        self.admin_login()
        response = self.client.post(
            "/devices",
            json={"device_uid": "duplicate-device", "label": "Duplicate"},
        )

        self.assertEqual(response.status_code, 409)

    def test_missing_or_invalid_device_token_is_rejected(self):
        response_missing = self.client.get("/api/v1/audit-requests/pending")
        self.assertEqual(response_missing.status_code, 401)

        response_invalid = self.device_get(
            "/api/v1/audit-requests/pending", "invalid-test-token"
        )
        self.assertEqual(response_invalid.status_code, 401)

    def test_device_only_receives_its_own_pending_requests(self):
        token_a = self.create_device("device-A")
        token_b = self.create_device("device-B")

        created = self.create_audit_request("device-A")
        self.assertEqual(created.status_code, 201, created.get_json())

        pending_a = self.device_get(
            "/api/v1/audit-requests/pending", token_a
        )
        pending_b = self.device_get(
            "/api/v1/audit-requests/pending", token_b
        )

        self.assertEqual(pending_a.status_code, 200)
        self.assertEqual(pending_b.status_code, 200)
        self.assertEqual(len(pending_a.get_json()), 1)
        self.assertEqual(len(pending_b.get_json()), 0)

    def test_device_can_submit_its_own_result_only_once(self):
        token = self.create_device("result-device")
        created = self.create_audit_request("result-device")
        self.assertEqual(created.status_code, 201, created.get_json())

        request_id = created.get_json()["request_id"]
        result_path = f"/api/v1/audit-requests/{request_id}/result"

        first = self.device_post(
            result_path, token, {"result": {"items_count": 0}}
        )
        self.assertEqual(first.status_code, 200, first.get_json())
        self.assertEqual(first.get_json()["status"], "completed")

        second = self.device_post(
            result_path, token, {"result": {"items_count": 0}}
        )
        self.assertEqual(second.status_code, 404)

    def test_disabled_storage_audit_rejects_new_request(self):
        self.create_device("disabled-feature-device")
        self.admin_login()

        toggle = self.client.post(
            "/admin/features/storage_audit",
            json={"enabled": False},
        )
        self.assertEqual(toggle.status_code, 200, toggle.get_json())

        response = self.create_audit_request("disabled-feature-device")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "feature_disabled")


    def test_disabled_storage_audit_is_hidden_from_pending_queue(self):
        token = self.create_device("hidden-pending-device")
        created = self.create_audit_request("hidden-pending-device")
        self.assertEqual(created.status_code, 201, created.get_json())

        self.admin_login()
        toggle = self.client.post(
            "/admin/features/storage_audit",
            json={"enabled": False},
        )
        self.assertEqual(toggle.status_code, 200, toggle.get_json())

        pending = self.device_get("/api/v1/audit-requests/pending", token)
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.get_json(), [])

    def test_disabled_storage_audit_rejects_result_submission(self):
        token = self.create_device("disabled-result-device")
        created = self.create_audit_request("disabled-result-device")
        self.assertEqual(created.status_code, 201, created.get_json())
        request_id = created.get_json()["request_id"]

        self.admin_login()
        toggle = self.client.post(
            "/admin/features/storage_audit",
            json={"enabled": False},
        )
        self.assertEqual(toggle.status_code, 200, toggle.get_json())

        response = self.device_post(
            f"/api/v1/audit-requests/{request_id}/result",
            token,
            {"result": {"items_count": 0}},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "feature_disabled")

    def test_oversized_audit_result_is_rejected(self):
        token = self.create_device("oversized-result-device")
        created = self.create_audit_request("oversized-result-device")
        self.assertEqual(created.status_code, 201, created.get_json())
        request_id = created.get_json()["request_id"]

        response = self.device_post(
            f"/api/v1/audit-requests/{request_id}/result",
            token,
            {"result": {"payload": "x" * (256 * 1024 + 100)}},
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["error"], "result_too_large")



    def test_heartbeat_marks_device_online(self):
        token = self.create_device("heartbeat-device")
        response = self.device_post(
            "/api/v1/device/heartbeat", token, {}
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data["device_uid"], "heartbeat-device")
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["offline_after_seconds"], 90)
        self.assertTrue(data["last_seen"])

    def test_device_list_reports_online_then_offline(self):
        token = self.create_device("connection-state-device")

        # A successful authenticated heartbeat updates last_seen.
        heartbeat = self.device_post(
            "/api/v1/device/heartbeat", token, {}
        )
        self.assertEqual(heartbeat.status_code, 200)

        self.admin_login()
        response = self.client.get("/devices")
        self.assertEqual(response.status_code, 200, response.get_json())
        item = next(
            d for d in response.get_json()
            if d["device_uid"] == "connection-state-device"
        )
        self.assertEqual(item["connection_status"], "online")

        # Simulate an old heartbeat in the isolated test database.
        db = sqlite3.connect(self.db_path)
        try:
            db.execute(
                "UPDATE devices SET last_seen=datetime('now','-5 minutes') "
                "WHERE device_uid=?",
                ("connection-state-device",),
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/devices")
        item = next(
            d for d in response.get_json()
            if d["device_uid"] == "connection-state-device"
        )
        self.assertEqual(item["connection_status"], "offline")

    def test_disabled_device_is_reported_offline(self):
        token = self.create_device("disabled-state-device")
        self.device_post("/api/v1/device/heartbeat", token, {})

        self.admin_login()
        db = sqlite3.connect(self.db_path)
        try:
            db.execute(
                "UPDATE devices SET enabled=0 WHERE device_uid=?",
                ("disabled-state-device",),
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/devices")
        item = next(
            d for d in response.get_json()
            if d["device_uid"] == "disabled-state-device"
        )
        self.assertEqual(item["connection_status"], "offline")


    def test_admin_disconnect_revokes_device_token(self):
        token = self.create_device("disconnect-device")
        self.admin_login()
        response = self.client.post(
            "/admin/devices/disconnect-device/connection",
            json={"enabled": False},
        )
        self.assertEqual(response.status_code, 200, response.get_json())

        blocked = self.device_get("/api/v1/audit-requests/pending", token)
        self.assertEqual(blocked.status_code, 401)

    def test_disconnect_cancels_queued_requests(self):
        token = self.create_device("cancel-queue-device")
        created = self.create_audit_request("cancel-queue-device")
        self.assertEqual(created.status_code, 201, created.get_json())

        self.admin_login()
        response = self.client.post(
            "/admin/devices/cancel-queue-device/connection",
            json={"enabled": False},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["cancelled_requests"], 1)

        db = sqlite3.connect(self.db_path)
        try:
            row = db.execute(
                "SELECT status FROM audit_requests WHERE id=?",
                (created.get_json()["request_id"],),
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(row[0], "cancelled")
        self.assertEqual(
            self.device_get("/api/v1/audit-requests/pending", token).status_code,
            401,
        )

    def test_admin_reconnect_restores_existing_device_token(self):
        token = self.create_device("reconnect-device")
        self.admin_login()
        disabled = self.client.post(
            "/admin/devices/reconnect-device/connection",
            json={"enabled": False},
        )
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(
            self.device_get("/api/v1/audit-requests/pending", token).status_code,
            401,
        )

        enabled = self.client.post(
            "/admin/devices/reconnect-device/connection",
            json={"enabled": True},
        )
        self.assertEqual(enabled.status_code, 200, enabled.get_json())
        self.assertEqual(
            self.device_get("/api/v1/audit-requests/pending", token).status_code,
            200,
        )

if __name__ == "__main__":
    unittest.main()
