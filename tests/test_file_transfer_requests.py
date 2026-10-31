import os
import tempfile
import unittest

from app import create_app
from modules.db import connect


class FileTransferRequestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "transfer-request-test-secret",
            "DATABASE_PATH": os.path.join(self.tmp.name, "test.db"),
        })
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["admin_username"] = "test-admin"

        with self.app.app_context():
            db = connect()
            db.execute(
                """INSERT INTO devices (device_uid, label, token_hash, enabled)
                   VALUES (?, ?, ?, 1)""",
                ("transfer-device-01", "Transfer test device", "test-hash"),
            )
            device_id = db.execute(
                "SELECT id FROM devices WHERE device_uid=?",
                ("transfer-device-01",),
            ).fetchone()["id"]
            db.execute(
                """INSERT INTO file_audit_manifests
                   (device_id, manifest_token, consent_version, item_count,
                    total_size_bytes, manifest_sha256)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (device_id, "transfer-manifest-01", "v1", 1, 1234, "a" * 64),
            )
            manifest_id = db.execute(
                "SELECT id FROM file_audit_manifests WHERE manifest_token=?",
                ("transfer-manifest-01",),
            ).fetchone()["id"]
            db.execute(
                """INSERT INTO file_audit_items
                   (manifest_id, item_token, relative_name, size_bytes,
                    mime_type, sha256)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (manifest_id, "internal-item-token", "survey/report.pdf",
                 1234, "application/pdf", "b" * 64),
            )
            self.item_id = db.execute(
                "SELECT id FROM file_audit_items WHERE manifest_id=?",
                (manifest_id,),
            ).fetchone()["id"]
            db.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_requires_admin(self):
        with self.client.session_transaction() as session:
            session.clear()
        response = self.client.post(
            "/admin/file-audit/transfers", json={"item_id": self.item_id}
        )
        self.assertIn(response.status_code, (302, 303))

    def test_invalid_item_id_rejected(self):
        for value in (None, True, 0, -1, "1"):
            response = self.client.post(
                "/admin/file-audit/transfers", json={"item_id": value}
            )
            self.assertEqual(response.status_code, 400)

    def test_request_proceeds_directly(self):
        response = self.client.post(
            "/admin/file-audit/transfers", json={"item_id": self.item_id}
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        data = response.get_json()
        self.assertEqual(data["status"], "pending")
        self.assertFalse(data["content_received"])
        self.assertEqual(data["expected_size_bytes"], 1234)

        with self.app.app_context():
            db = connect()
            transfer = db.execute(
                "SELECT * FROM file_transfers WHERE item_id=?", (self.item_id,)
            ).fetchone()

        self.assertEqual(transfer["received_bytes"], 0)
        self.assertEqual(transfer["expected_sha256"], "b" * 64)
        self.assertEqual(transfer["status"], "pending")

    def test_duplicate_request_does_not_create_second_transfer(self):
        first = self.client.post(
            "/admin/file-audit/transfers", json={"item_id": self.item_id}
        )
        second = self.client.post(
            "/admin/file-audit/transfers", json={"item_id": self.item_id}
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.get_json()["already_requested"])
        self.assertEqual(
            first.get_json()["transfer_id"], second.get_json()["transfer_id"]
        )

    def test_missing_item_returns_404(self):
        response = self.client.post(
            "/admin/file-audit/transfers", json={"item_id": 999999}
        )
        self.assertEqual(response.status_code, 404)

    def test_disabled_feature_rejects_request(self):
        with self.app.app_context():
            db = connect()
            db.execute("UPDATE feature_flags SET enabled=0 WHERE name='file_transfer'")
            db.commit()
        response = self.client.post(
            "/admin/file-audit/transfers", json={"item_id": self.item_id}
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
