import tempfile, os, unittest
from app import create_app

class BasicAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING":True,"SECRET_KEY":"test-secret",
                               "DATABASE_PATH":os.path.join(self.tmp.name,"test.db")})
        self.client = self.app.test_client()
    def tearDown(self):
        self.tmp.cleanup()
    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json["status"],"ok")
    def test_login_page(self):
        r = self.client.get("/auth/login")
        self.assertEqual(r.status_code,200)

if __name__ == "__main__":
    unittest.main()
