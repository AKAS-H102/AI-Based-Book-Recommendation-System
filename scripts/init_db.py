"""
Creates the SQLite database and loads the cleaned dataset into it.

 * books            <- data/processed/books_clean.csv
 * seed users       <- one demo account per user_id in ratings_clean.csv  (username reader001 ...)
 * seed ratings     <- data/processed/ratings_clean.csv   (this is the "community" the CF model learns from)
 * demo account     <- username: demo   password: demo1234   (no ratings, great for live demonstration)

Run:  python scripts/init_db.py          (add --reset to delete and rebuild the database)
"""
import argparse
import os
import sqlite3
import sys

import pandas as pd
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import init_schema          # noqa: E402
from config import Config               # noqa: E402


def build_database(db_path, data_dir, max_users=None):
    """Create tables and load books + seed users + seed ratings. Returns (n_books, n_users, n_ratings)."""
    books_f, ratings_f = os.path.join(data_dir, "books_clean.csv"), os.path.join(data_dir, "ratings_clean.csv")
    if not (os.path.exists(books_f) and os.path.exists(ratings_f)):
        raise FileNotFoundError("Processed data not found. Run:  python -m ml.make_sample_data && python -m ml.preprocess")
    init_schema(db_path)
    con = sqlite3.connect(db_path)
    if con.execute("SELECT COUNT(*) FROM books").fetchone()[0]:
        con.close()
        raise RuntimeError("Database already contains books. Use --reset to rebuild it.")

    books = pd.read_csv(books_f).fillna({"description": "", "cover_url": ""})
    ratings = pd.read_csv(ratings_f)
    if max_users:
        ratings = ratings[ratings.user_id.isin(sorted(ratings.user_id.unique())[:max_users])]
    con.executemany(
        "INSERT INTO books(id,title,author,year,genres,description,cover_url) VALUES (?,?,?,?,?,?,?)",
        [(int(r.book_id), r.title, r.author, None if pd.isna(r.year) else int(r.year), r.genres, r.description, r.cover_url)
         for r in books.itertuples()])

    shared_hash = generate_password_hash("seed-account-no-login-" + os.urandom(8).hex())   # seed users cannot log in
    uid_map = {}
    for u in sorted(ratings.user_id.unique()):
        cur = con.execute("INSERT INTO users(username,email,password_hash,is_seed) VALUES (?,?,?,1)",
                          (f"reader{int(u):03d}", f"reader{int(u):03d}@example.com", shared_hash))
        uid_map[u] = cur.lastrowid
    con.executemany("INSERT INTO ratings(user_id,book_id,rating) VALUES (?,?,?)",
                    [(uid_map[r.user_id], int(r.book_id), int(r.rating)) for r in ratings.itertuples()])
    con.execute("INSERT INTO users(username,email,password_hash,preferred_genres) VALUES (?,?,?,?)",
                ("demo", "demo@example.com", generate_password_hash("demo1234"), "Fantasy;Science Fiction"))
    con.execute("""UPDATE books SET
                     avg_rating = COALESCE((SELECT ROUND(AVG(rating),2) FROM ratings WHERE book_id=books.id),0),
                     ratings_count = (SELECT COUNT(*) FROM ratings WHERE book_id=books.id)""")
    con.commit()
    con.close()
    return len(books), len(uid_map), len(ratings)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--db", default=Config.DATABASE)
    ap.add_argument("--data", default=Config.PROCESSED_DIR)
    a = ap.parse_args()
    if a.reset and os.path.exists(a.db):
        os.remove(a.db)
    try:
        nb, nu, nr = build_database(a.db, a.data)
    except (FileNotFoundError, RuntimeError) as e:
        sys.exit(str(e))
    print(f"Database ready: {a.db}")
    print(f"  books={nb}  seed users={nu}  seed ratings={nr}")
    print("  Demo login ->  username: demo   password: demo1234")


if __name__ == "__main__":
    main()
