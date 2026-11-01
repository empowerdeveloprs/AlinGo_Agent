import os
import sqlite3
import tempfile
import unittest

from app import create_app


class OptionalFeatureFlagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "optional-features.db")
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "optional-feature-test-secret",
            "DATABASE_PATH": self.db_path,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def admin_login(self):
        with self.client.session_transaction() as session:
            session["admin_username"] = "test-admin"

    def get_flag(self, name):
        db = sqlite3.connect(self.db_path)
        try:
            row = db.execute(
                "SELECT enabled FROM feature_flags WHERE name = ?",
                (name,),
            ).fetchone()
            return None if row is None else row[0]
        finally:
            db.close()

    def test_new_features_are_disabled_by_default(self):
        self.assertEqual(self.get_flag("screen_viewer"), 0)
        self.assertEqual(self.get_flag("typing_diagnostics"), 0)

    def test_admin_can_toggle_screen_viewer_independently(self):
        self.admin_login()

        response = self.client.post(
            "/admin/features/screen_viewer",
            json={"enabled": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_flag("screen_viewer"), 1)
        self.assertEqual(self.get_flag("typing_diagnostics"), 0)

        response = self.client.post(
            "/admin/features/screen_viewer",
            json={"enabled": False},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_flag("screen_viewer"), 0)

    def test_admin_can_toggle_typing_diagnostics_independently(self):
        self.admin_login()

        response = self.client.post(
            "/admin/features/typing_diagnostics",
            json={"enabled": True},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_flag("typing_diagnostics"), 1)
        self.assertEqual(self.get_flag("screen_viewer"), 0)


if __name__ == "__main__":
    unittest.main()
