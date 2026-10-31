import os
import tempfile
import unittest

from app import create_app


class FileAuditStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "file-audit-test-secret",
            "DATABASE_PATH": os.path.join(self.tmp.name, "test.db"),
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_requires_admin_session(self):
        response = self.client.get("/admin/file-audit/status")
        self.assertIn(response.status_code, (302, 303))

    def test_admin_can_read_status_without_transferring_files(self):
        with self.client.session_transaction() as session:
            session["admin_username"] = "test-admin"

        response = self.client.get("/admin/file-audit/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["feature"], "file_transfer")
        self.assertTrue(data["enabled"])
        self.assertFalse(data["content_transfer_implemented"])

    def test_manifest_list_requires_admin_session(self):
        response = self.client.get("/admin/file-audit/manifests")
        self.assertIn(response.status_code, (302, 303))

    def test_manifest_list_is_empty_when_feature_disabled(self):
        from modules.db import connect

        with self.client.session_transaction() as session:
            session["admin_username"] = "test-admin"

        with self.app.app_context():
            db = connect()
            db.execute(
                "UPDATE feature_flags SET enabled=0 WHERE name='file_transfer'"
            )
            db.commit()

        response = self.client.get("/admin/file-audit/manifests")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["enabled"])
        self.assertEqual(data["manifests"], [])
        self.assertFalse(data["content_transferred_by_this_endpoint"])

    def test_manifest_list_returns_all_items_without_internal_tokens(self):
        from modules.db import connect

        with self.client.session_transaction() as session:
            session["admin_username"] = "test-admin"

        with self.app.app_context():
            db = connect()
            db.execute(
                """INSERT INTO devices
                   (device_uid, label, token_hash, enabled)
                   VALUES (?, ?, ?, 1)""",
                ("test-device-001", "Test device", "not-a-real-token-hash"),
            )
            device_id = db.execute(
                "SELECT id FROM devices WHERE device_uid=?",
                ("test-device-001",),
            ).fetchone()["id"]

            db.execute(
                """INSERT INTO file_audit_manifests
                   (device_id, manifest_token, consent_version, item_count,
                    total_size_bytes, manifest_sha256)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (device_id, "internal-manifest-token", "v1", 3, 600, "a" * 64),
            )
            manifest_id = db.execute(
                "SELECT id FROM file_audit_manifests WHERE manifest_token=?",
                ("internal-manifest-token",),
            ).fetchone()["id"]

            for n, size in enumerate((100, 200, 300), start=1):
                db.execute(
                    """INSERT INTO file_audit_items
                       (manifest_id, item_token, relative_name, size_bytes,
                        mime_type, sha256)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        manifest_id,
                        f"internal-item-token-{n}",
                        f"survey/file-{n}.pdf",
                        size,
                        "application/pdf",
                        str(n) * 64,
                    ),
                )
            db.commit()

        response = self.client.get("/admin/file-audit/manifests?limit=1")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertTrue(data["enabled"])
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["manifests"]), 1)

        manifest = data["manifests"][0]
        self.assertEqual(manifest["item_count"], 3)
        self.assertEqual(len(manifest["items"]), 3)
        self.assertEqual(
            sum(item["size_bytes"] for item in manifest["items"]),
            600,
        )

        self.assertNotIn("manifest_token", manifest)
        for item in manifest["items"]:
            self.assertNotIn("item_token", item)

        self.assertFalse(data["content_transferred_by_this_endpoint"])
