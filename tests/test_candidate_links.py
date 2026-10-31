import os
import tempfile
import unittest
from app import create_app

class CandidateLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "candidate-test-secret",
            "DATABASE_PATH": os.path.join(self.tmp.name, "candidate-test.db"),
        })
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["admin_username"] = "candidate-admin"

    def tearDown(self):
        self.tmp.cleanup()

    def create_link(self):
        r = self.client.post("/candidate/admin/links", json={
            "candidate_label": "Test candidate", "valid_hours": 24
        })
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        return r.get_json()["token_once"]

    def test_admin_creates_link_and_public_sop_opens(self):
        token = self.create_link()
        with self.client.session_transaction() as sess:
            sess.clear()
        r = self.client.get(f"/candidate/{token}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("معلومات", r.get_data(as_text=True))

    def test_survey_blocked_before_consent(self):
        token = self.create_link()
        r = self.client.post(f"/candidate/{token}/permissions", data={
            "report": '{"location":true,"camera":true}'
        })
        self.assertEqual(r.status_code, 403)

    def test_survey_blocked_if_permission_report_incomplete(self):
        token = self.create_link()
        self.client.post(f"/candidate/{token}/consent", data={"agree":"yes"})
        r = self.client.post(f"/candidate/{token}/permissions", data={
            "report": '{"location":true,"camera":false}'
        })
        self.assertEqual(r.status_code, 403)

    def test_invalid_link_rejected(self):
        r = self.client.get("/candidate/not-a-real-token")
        self.assertEqual(r.status_code, 410)

    def test_revoked_link_rejected(self):
        token = self.create_link()
        with self.app.app_context():
            from modules.db import connect
            from modules.security import hash_token
            row = connect().execute(
                "SELECT id FROM candidate_links WHERE token_hash=?", (hash_token(token),)
            ).fetchone()
            link_id = row["id"]
        r = self.client.post(f"/candidate/admin/links/{link_id}/revoke")
        self.assertEqual(r.status_code, 200)
        with self.client.session_transaction() as sess:
            sess.clear()
        r = self.client.get(f"/candidate/{token}")
        self.assertEqual(r.status_code, 410)

    def test_permission_gate_then_survey_submission(self):
        token = self.create_link()
        self.client.post(f"/candidate/{token}/consent", data={"agree":"yes"})
        r = self.client.post(f"/candidate/{token}/permissions", data={
            "report": '{"location":true,"camera":true}'
        })
        self.assertEqual(r.status_code, 200)

        r = self.client.post(f"/candidate/{token}/submit", data={
            "statement": "First response"
        })
        self.assertEqual(r.status_code, 200)

        # A second submission must not overwrite the first response.
        r = self.client.post(f"/candidate/{token}/submit", data={
            "statement": "Changed response"
        })
        self.assertEqual(r.status_code, 409)

        from modules.db import connect
        from modules.security import hash_token
        import json

        with self.app.app_context():
            db = connect()
            try:
                row = db.execute(
                    "SELECT survey_json FROM candidate_links WHERE token_hash=?",
                    (hash_token(token),)
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(
                    json.loads(row["survey_json"])["statement"],
                    "First response"
                )
            finally:
                db.close()

if __name__ == "__main__":
    unittest.main()
