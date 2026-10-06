import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import create_app                      # noqa: E402
from scripts.init_db import build_database      # noqa: E402


class AppTestCase(unittest.TestCase):
    """Creates a fresh temporary database (all books + 80 seed users) for every test."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        build_database(self.db_path, os.path.join(ROOT, "data", "processed"), max_users=80)
        self.app = create_app({"TESTING": True, "DATABASE": self.db_path, "MODEL_REFIT_SECONDS": 0, "SECRET_KEY": "test"})
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    # ---- helpers
    def token(self):
        self.client.get("/login")
        with self.client.session_transaction() as s:
            return s["csrf"]

    def post(self, url, data=None, **kw):
        data = dict(data or {})
        data["csrf_token"] = self.token()
        return self.client.post(url, data=data, **kw)

    def api(self, method, url, json=None):
        return getattr(self.client, method)(url, json=json, headers={"X-CSRF-Token": self.token()})

    def register(self, username="alice", email="alice@example.com", password="secret123", genres=()):
        return self.post("/register", {"username": username, "email": email, "password": password,
                                       "confirm": password, "genres": list(genres)}, follow_redirects=True)

    def login(self, ident="alice", password="secret123"):
        return self.post("/login", {"identifier": ident, "password": password}, follow_redirects=True)
