import os
import tempfile
import unittest

from app import create_app


class DeviceManifestIngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "device-manifest-test-secret",
            "DATABASE_PATH": os.path.join(self.tmp.name, "test.db"),
        })
        self.client = self.app.test_client()
        self.token = self._register_device("manifest-device-01")

    def tearDown(self):
        self.tmp.cleanup()

    def _register_device(self, uid):
        with self.client.session_transaction() as session:
            session["admin_username"] = "test-admin"
        response = self.client.post(
            "/devices",
            json={"device_uid": uid, "label": "Manifest test device"},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        token = response.get_json()["token_once"]
        with self.client.session_transaction() as session:
            session.clear()
        return token

    def _post(self, payload, token=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return self.client.post(
            "/api/v1/device/file-audit/manifests",
            json=payload,
            headers=headers,
        )

    def _payload(self, **overrides):
        payload = {
            "consent_granted": True,
            "consent_version": "v1",
            "manifest_token": "manifest-test-token-001",
            "items": [
                {
                    "relative_name": "survey/forms/form-a.pdf",
                    "size_bytes": 100,
                    "mime_type": "application/pdf",
                    "sha256": "a" * 64,
                    "modified_at": "2026-10-29T10:00:00Z",
                },
                {
                    "relative_name": "survey/photos/photo-b.jpg",
                    "size_bytes": 250,
                    "mime_type": "image/jpeg",
                },
            ],
        }
        payload.update(overrides)
        return payload

    def test_missing_or_invalid_token_rejected(self):
        self.assertEqual(self._post(self._payload()).status_code, 401)
        self.assertEqual(
            self._post(self._payload(), "not-a-valid-token").status_code,
            401,
        )

    def test_manifest_requires_explicit_consent(self):
        response = self._post(self._payload(consent_granted=False), self.token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "explicit_consent_required")

    def test_valid_manifest_stores_metadata_and_computed_totals(self):
        response = self._post(self._payload(), self.token)
        self.assertEqual(response.status_code, 201, response.get_json())
        result = response.get_json()
        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["total_size_bytes"], 350)
        self.assertFalse(result["content_received"])

        from modules.db import connect
        with self.app.app_context():
            db = connect()
            manifest = db.execute(
                "SELECT * FROM file_audit_manifests WHERE id=?",
                (result["manifest_id"],),
            ).fetchone()
            items = db.execute(
                "SELECT * FROM file_audit_items WHERE manifest_id=? ORDER BY id",
                (result["manifest_id"],),
            ).fetchall()

        self.assertEqual(manifest["item_count"], 2)
        self.assertEqual(manifest["total_size_bytes"], 350)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["relative_name"], "survey/forms/form-a.pdf")
        self.assertEqual(items[0]["transfer_status"], "metadata_only")
        self.assertEqual(items[0]["transferred_bytes"], 0)

    def test_unsafe_path_rejected(self):
        for bad_name in ("../secret.txt", "/absolute/file", "a/../b", "a\\b"):
            payload = self._payload(items=[{
                "relative_name": bad_name,
                "size_bytes": 1,
            }])
            response = self._post(payload, self.token)
            self.assertEqual(response.status_code, 400, bad_name)

    def test_invalid_size_or_digest_rejected(self):
        for size in (-1, True, "100"):
            response = self._post(self._payload(items=[{
                "relative_name": "survey/file.pdf",
                "size_bytes": size,
            }]), self.token)
            self.assertEqual(response.status_code, 400)

        response = self._post(self._payload(items=[{
            "relative_name": "survey/file.pdf",
            "size_bytes": 1,
            "sha256": "not-a-digest",
        }]), self.token)
        self.assertEqual(response.status_code, 400)

    def test_duplicate_manifest_is_idempotent(self):
        first = self._post(self._payload(), self.token)
        second = self._post(self._payload(), self.token)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            first.get_json()["manifest_id"],
            second.get_json()["manifest_id"],
        )
        self.assertEqual(second.get_json()["status"], "already_received")

    def test_reused_token_with_different_payload_conflicts(self):
        self.assertEqual(self._post(self._payload(), self.token).status_code, 201)
        changed = self._payload(items=[{
            "relative_name": "survey/changed.pdf",
            "size_bytes": 999,
        }])
        response = self._post(changed, self.token)
        self.assertEqual(response.status_code, 409)

    def test_manifest_token_cannot_be_reused_by_another_device(self):
        self.assertEqual(self._post(self._payload(), self.token).status_code, 201)
        other_token = self._register_device("manifest-device-02")
        response = self._post(self._payload(), other_token)
        self.assertEqual(response.status_code, 409)

    def test_disabled_feature_rejects_manifest(self):
        from modules.db import connect
        with self.app.app_context():
            db = connect()
            db.execute(
                "UPDATE feature_flags SET enabled=0 WHERE name='file_transfer'"
            )
            db.commit()

        response = self._post(self._payload(), self.token)
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
