"""Functional + integration tests for the web app and API (each test uses a fresh temp database)."""
import sqlite3
import unittest
from tests.base import AppTestCase


class AuthTests(AppTestCase):
    def test_register_success_logs_in_and_hashes_password(self):
        r = self.register()
        self.assertIn(b"account has been created", r.data)
        con = sqlite3.connect(self.db_path)
        pw = con.execute("SELECT password_hash FROM users WHERE username='alice'").fetchone()[0]
        self.assertNotIn("secret123", pw)
        self.assertTrue(pw.startswith(("scrypt:", "pbkdf2:")))

    def test_register_validation_errors(self):
        for kw, msg in [({"username": "a"}, b"Username must be"), ({"email": "bad"}, b"valid email"),
                        ({"password": "short"}, b"at least 8"), ({"password": "onlyletters"}, b"letter and a number")]:
            r = self.register(**kw)
            self.assertEqual(r.status_code, 400)
            self.assertIn(msg, r.data)

    def test_duplicate_username_or_email_rejected_case_insensitive(self):
        self.register()
        self.client.get("/logout")
        r = self.register(username="ALICE", email="other@example.com")
        self.assertIn(b"already registered", r.data)

    def test_login_logout_flow(self):
        self.register()
        self.post("/logout")
        self.assertEqual(self.client.get("/favorites").status_code, 302)       # logged out -> redirect to login
        r = self.login()
        self.assertIn(b"Welcome back", r.data)
        self.assertEqual(self.client.get("/profile").status_code, 200)

    def test_wrong_password_rejected(self):
        self.register(); self.post("/logout")
        r = self.login(password="wrongpass1")
        self.assertEqual(r.status_code, 401)
        self.assertIn(b"Invalid username", r.data)

    def test_login_throttling_after_repeated_failures(self):
        self.register(); self.post("/logout")
        for _ in range(5):
            self.login(password="bad")
        r = self.login(password="bad")
        self.assertEqual(r.status_code, 429)

    def test_open_redirect_blocked(self):
        self.register(); self.post("/logout")
        r = self.post("/login?next=//evil.com", {"identifier": "alice", "password": "secret123"})
        self.assertNotIn("evil.com", r.headers["Location"])

    def test_missing_csrf_token_rejected(self):
        r = self.client.post("/login", data={"identifier": "x", "password": "y"})
        self.assertEqual(r.status_code, 400)

    def test_seed_users_cannot_log_in(self):
        r = self.login("reader001", "anything123")
        self.assertEqual(r.status_code, 401)


class BookTests(AppTestCase):
    def test_pages_render(self):
        for url in ["/", "/books", "/books/1", "/about", "/login", "/register"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_unknown_book_404(self):
        self.assertEqual(self.client.get("/books/99999").status_code, 404)

    def test_search_by_title_and_author(self):
        self.assertIn(b"The Hobbit", self.client.get("/books?q=hobbit").data)
        self.assertIn(b"Tolkien", self.client.get("/books?author=tolkien").data)

    def test_filter_by_genre_and_rating(self):
        data = self.client.get("/api/books?genre=Horror&per_page=50").get_json()
        self.assertGreater(data["total"], 3)
        self.assertTrue(all("Horror" in b["genres"] for b in data["books"]))
        hi = self.client.get("/api/books?min_rating=4.0&per_page=50").get_json()
        self.assertTrue(all(b["avg_rating"] >= 4.0 for b in hi["books"]))

    def test_sort_and_pagination(self):
        d = self.client.get("/api/books?sort=title&per_page=5&page=2").get_json()
        titles = [b["title"].lower() for b in d["books"]]
        self.assertEqual(len(titles), 5)
        self.assertEqual(titles, sorted(titles))

    def test_sql_injection_attempt_is_harmless(self):
        r = self.client.get("/api/books?q=' OR 1=1; DROP TABLE books;--")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["total"], 0)
        self.assertGreater(self.client.get("/api/books").get_json()["total"], 50)

    def test_xss_is_escaped(self):
        r = self.client.get("/books?q=<script>alert(1)</script>")
        self.assertNotIn(b"<script>alert(1)</script>", r.data)

    def test_bad_query_params_return_400(self):
        self.assertEqual(self.client.get("/api/books?page=abc").status_code, 400)


class InteractionTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.register(genres=["Fantasy"])

    def test_rating_requires_login(self):
        c = self.app.test_client()
        c.get("/login")
        with c.session_transaction() as s:
            t = s["csrf"]
        r = c.post("/api/books/1/rate", json={"rating": 5}, headers={"X-CSRF-Token": t})
        self.assertEqual(r.status_code, 401)

    def test_rate_updates_average_and_history(self):
        before = self.client.get("/api/books/1").get_json()
        r = self.api("post", "/api/books/1/rate", {"rating": 5}).get_json()
        self.assertEqual(r["my_rating"], 5)
        self.assertEqual(r["ratings_count"], before["ratings_count"] + 1)
        self.api("post", "/api/books/1/rate", {"rating": 2})           # change rating -> no new row
        after = self.client.get("/api/books/1").get_json()
        self.assertEqual(after["ratings_count"], before["ratings_count"] + 1)
        self.assertEqual(after["my_rating"], 2)
        hist = self.client.get("/api/me/history").get_json()["history"]
        self.assertEqual([h["action"] for h in hist[:2]], ["rate", "rate"])

    def test_invalid_ratings_rejected(self):
        for bad in [0, 6, -1, "5", 4.5, None, True]:
            self.assertEqual(self.api("post", "/api/books/1/rate", {"rating": bad}).status_code, 400, bad)
        self.assertEqual(self.api("post", "/api/books/99999/rate", {"rating": 3}).status_code, 404)

    def test_remove_rating(self):
        self.api("post", "/api/books/2/rate", {"rating": 4})
        r = self.api("delete", "/api/books/2/rate").get_json()
        self.assertIsNone(r["my_rating"])
        self.assertIsNone(self.client.get("/api/books/2").get_json()["my_rating"])

    def test_favorite_toggle_and_list(self):
        self.assertTrue(self.api("post", "/api/books/3/favorite").get_json()["favorite"])
        self.assertIn(b"Harry Potter", self.client.get("/favorites").data)
        favs = self.client.get("/api/me/favorites").get_json()["favorites"]
        self.assertEqual([b["id"] for b in favs], [3])
        self.assertFalse(self.api("post", "/api/books/3/favorite").get_json()["favorite"])
        self.assertEqual(self.client.get("/api/me/favorites").get_json()["favorites"], [])

    def test_viewing_a_book_is_logged_once_within_10_minutes(self):
        self.client.get("/books/5"); self.client.get("/books/5")
        views = [h for h in self.client.get("/api/me/history").get_json()["history"] if h["action"] == "view"]
        self.assertEqual(len(views), 1)

    def test_history_page_and_profile_update(self):
        self.api("post", "/api/books/1/rate", {"rating": 5})
        self.assertIn(b"My ratings (1)", self.client.get("/history").data)
        r = self.post("/profile", {"full_name": "Alice A", "bio": "hi", "genres": ["Horror", "Romance"]}, follow_redirects=True)
        self.assertIn(b"Profile updated", r.data)
        con = sqlite3.connect(self.db_path)
        self.assertEqual(con.execute("SELECT preferred_genres FROM users WHERE username='alice'").fetchone()[0], "Horror;Romance")


class RecommendationIntegrationTests(AppTestCase):
    """Whole flow: register -> rate/favourite -> recommendations change and are explained."""

    def titles(self, recs):
        return [b["title"] for b in recs]

    def test_cold_start_uses_selected_genres(self):
        self.register(genres=["Horror"])
        recs = self.client.get("/api/recommendations?k=6").get_json()["recommendations"]
        self.assertEqual(len(recs), 6)
        self.assertGreaterEqual(sum("Horror" in b["genres"] for b in recs), 3)
        self.assertTrue(all(b["reasons"] and 0 <= b["match_pct"] <= 100 for b in recs))

    def test_recommendations_adapt_to_ratings_and_exclude_rated(self):
        self.register()
        books = self.client.get("/api/books?per_page=50&genre=Romance").get_json()["books"]
        for b in books[:4]:
            self.api("post", f"/api/books/{b['id']}/rate", {"rating": 5})
        recs = self.client.get("/api/recommendations?k=10").get_json()["recommendations"]
        rated = {b["id"] for b in books[:4]}
        self.assertFalse(rated & {b["id"] for b in recs})
        self.assertGreaterEqual(sum("Romance" in b["genres"] for b in recs), 4)

    def test_favorites_influence_recommendations(self):
        self.register()
        for b in self.client.get("/api/books?genre=Horror&per_page=4").get_json()["books"]:
            self.api("post", f"/api/books/{b['id']}/favorite")
        recs = self.client.get("/api/recommendations?k=8").get_json()["recommendations"]
        self.assertGreaterEqual(sum("Horror" in b["genres"] for b in recs), 3)

    def test_recommendation_page_and_genre_filter(self):
        self.register(genres=["Fantasy"])
        page = self.client.get("/recommendations").data
        self.assertIn(b"match", page); self.assertIn("💡".encode(), page)
        filtered = self.client.get("/api/recommendations?genre=Mystery&k=5").get_json()["recommendations"]
        self.assertTrue(all("Mystery" in b["genres"] for b in filtered))

    def test_similar_books_endpoint(self):
        s = self.client.get("/api/books/1/similar").get_json()["similar"]
        self.assertEqual(len(s), 6)
        self.assertNotIn(1, [b["id"] for b in s])

    def test_recommendations_require_login(self):
        self.assertEqual(self.client.get("/api/recommendations").status_code, 401)
        self.assertEqual(self.client.get("/recommendations").status_code, 302)


if __name__ == "__main__":
    unittest.main()
