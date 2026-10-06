"""Unit tests + recommendation-quality tests for the ML engine and preprocessing."""
import os
import unittest
import numpy as np
import pandas as pd
from tests.base import ROOT
from ml.engine import HybridRecommender
from ml.preprocess import clean
from ml.evaluate import split_ratings, _metrics

DATA = os.path.join(ROOT, "data", "processed")


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.books = pd.read_csv(os.path.join(DATA, "books_clean.csv"))
        cls.ratings = pd.read_csv(os.path.join(DATA, "ratings_clean.csv"))
        cls.model = HybridRecommender().fit(cls.books, cls.ratings)
        cls.title_id = dict(zip(cls.books.title, cls.books.book_id))
        cls.genres = dict(zip(cls.books.book_id, cls.books.genres))

    def test_returns_k_unique_items_with_reasons(self):
        recs = self.model.recommend({self.title_id["Dune"]: 5}, k=8)
        ids = [r["book_id"] for r in recs]
        self.assertEqual(len(ids), 8)
        self.assertEqual(len(set(ids)), 8)
        self.assertTrue(all(r["reasons"] for r in recs))

    def test_never_recommends_already_rated_books(self):
        seen = {self.title_id["Dune"]: 5, self.title_id["Foundation"]: 4}
        ids = {r["book_id"] for r in self.model.recommend(seen, k=20)}
        self.assertFalse(ids & set(seen))

    def test_cold_start_with_no_data_returns_popular_books(self):
        recs = self.model.recommend({}, k=5)
        self.assertEqual(len(recs), 5)
        self.assertIn("community", recs[0]["reasons"][0].lower())

    def test_genre_preference_influences_cold_start(self):
        recs = self.model.recommend({}, genres=["Horror"], k=6)
        horror = sum("Horror" in self.genres[r["book_id"]] for r in recs)
        self.assertGreaterEqual(horror, 4)

    def test_liked_scifi_gives_scifi_recommendations(self):
        liked = {self.title_id[t]: 5 for t in ["Dune", "Foundation", "Neuromancer", "The Martian"]}
        recs = self.model.recommend(liked, k=8)
        sf = sum("Science Fiction" in self.genres[r["book_id"]] for r in recs)
        self.assertGreaterEqual(sf, 5)
        self.assertTrue(any(r["components"]["collaborative"] > 0 for r in recs))   # CF signal must be active

    def test_low_ratings_push_genre_away(self):
        disliked = {self.title_id[t]: 1 for t in ["Dracula", "The Shining", "It", "Pet Sematary"]}
        liked = {self.title_id[t]: 5 for t in ["Pride and Prejudice", "Emma", "Jane Eyre"]}
        recs = self.model.recommend({**disliked, **liked}, k=8)
        horror = sum("Horror" in self.genres[r["book_id"]] for r in recs)
        self.assertLessEqual(horror, 1)

    def test_similar_books_excludes_itself(self):
        bid = self.title_id["The Hobbit"]
        sims = self.model.similar(bid, 5)
        self.assertEqual(len(sims), 5)
        self.assertNotIn(bid, [s["book_id"] for s in sims])
        self.assertIn("Fantasy", self.genres[sims[0]["book_id"]])

    def test_scores_are_between_0_and_1(self):
        for r in self.model.recommend({self.title_id["Dune"]: 5}, genres=["Fantasy"], k=10):
            self.assertTrue(0 <= r["score"] <= 1.0001)


class PreprocessTests(unittest.TestCase):
    def test_cleaning_handles_dirty_data(self):
        books = pd.DataFrame({
            "book_id": [1, 2, 3, 4, 5],
            "title": ["  Dune ", "dune", None, "Emma", "Ghost"],
            "authors": ["Frank Herbert", "frank herbert", "X", None, "Y"],
            "original_publication_year": [1965, 1965, 2000, 99999, None],
            "genres": ["science fiction;adventure", "", "Fantasy", "romance, classics", None],
            "description": ["A desert planet", None, "x", "", None]})
        ratings = pd.DataFrame({"user_id": [1, 1, 1, 1, 1, 2, 2, 2, 3],
                                "book_id": [1, 2, 4, 5, 5, 1, 4, 5, 1],
                                "rating": [5, 4, 3, 9, 4, 2, 5, 3, 4]})
        b, r, rep = clean(books, ratings, min_user_ratings=3)
        self.assertEqual(rep["duplicate_books_removed"], 1)         # "Dune" and "dune"
        self.assertEqual(rep["missing_titles_dropped"], 1)
        self.assertNotIn(2, b.book_id.values)
        self.assertEqual(b.loc[b.book_id == 1, "genres"].iloc[0], "Science Fiction;Adventure")
        self.assertTrue(b.year.isna().sum() >= 2)                   # 99999 and None
        self.assertTrue((b.author != "").all() and b.author.notna().all())
        self.assertTrue(r.rating.between(1, 5).all())               # rating 9 removed
        self.assertFalse(r.duplicated(["user_id", "book_id"]).any())
        self.assertNotIn(3, r.user_id.values)                       # user with <3 ratings dropped


class GoodbooksFormatTests(unittest.TestCase):
    def test_goodbooks_layout_with_tags(self):
        import tempfile
        d = tempfile.mkdtemp()
        pd.DataFrame({"book_id": [1, 2], "goodreads_book_id": [10, 20], "title": ["Dune", "Emma"],
                      "authors": ["Frank Herbert", "Jane Austen"], "original_publication_year": [1965.0, 1815.0],
                      "average_rating": [4.2, 4.0], "image_url": ["http://x/1.jpg", "http://x/2.jpg"]}).to_csv(f"{d}/books.csv", index=False)
        pd.DataFrame({"tag_id": [1, 2, 3], "tag_name": ["science-fiction", "classics", "to-read"]}).to_csv(f"{d}/tags.csv", index=False)
        pd.DataFrame({"goodreads_book_id": [10, 10, 20, 20], "tag_id": [1, 3, 2, 3], "count": [90, 500, 80, 400]}).to_csv(f"{d}/book_tags.csv", index=False)
        ratings = pd.DataFrame({"user_id": [1, 1, 1, 2, 2, 2], "book_id": [1, 2, 1, 1, 2, 2], "rating": [5, 4, 3, 2, 5, 4]})
        b, r, rep = clean(pd.read_csv(f"{d}/books.csv"), ratings, min_user_ratings=2, raw_dir=d)
        self.assertEqual(b.loc[b.book_id == 1, "genres"].iloc[0], "Science Fiction")   # "to-read" is not a genre
        self.assertEqual(b.loc[b.book_id == 2, "genres"].iloc[0], "Classics")
        self.assertEqual(rep["duplicate_ratings_removed"], 2)


class EvaluationTests(unittest.TestCase):
    def test_split_never_leaks(self):
        ratings = pd.read_csv(os.path.join(DATA, "ratings_clean.csv"))
        train, test = split_ratings(ratings)
        self.assertEqual(len(train) + len(test), len(ratings))
        merged = train.merge(test, on=["user_id", "book_id"])
        self.assertEqual(len(merged), 0)

    def test_metrics_perfect_and_zero(self):
        p, r, n, h = _metrics([1, 2, 3], {1, 2, 3}, 3)
        self.assertAlmostEqual(p, 1.0); self.assertAlmostEqual(n, 1.0); self.assertEqual(h, 1.0)
        p, r, n, h = _metrics([7, 8, 9], {1}, 3)
        self.assertEqual((p, r, n, h), (0, 0, 0, 0))

    def test_hybrid_beats_random_baseline(self):
        from ml.evaluate import evaluate
        books = pd.read_csv(os.path.join(DATA, "books_clean.csv"))
        ratings = pd.read_csv(os.path.join(DATA, "ratings_clean.csv"))
        df, _ = evaluate(books, ratings, k=10, max_users=120)
        self.assertGreater(df.loc["Hybrid (proposed)", "NDCG@10"], df.loc["Random", "NDCG@10"])
        self.assertGreater(df.loc["Hybrid (proposed)", "Precision@10"], df.loc["Random", "Precision@10"])


if __name__ == "__main__":
    unittest.main()
