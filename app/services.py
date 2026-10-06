"""Business logic shared by the web pages and the JSON API."""
import threading
import time
import pandas as pd
from flask import current_app
from ml.engine import HybridRecommender
from .db import get_db

SORTS = {
    "popular": "ratings_count DESC, avg_rating DESC",
    "rating": "avg_rating DESC, ratings_count DESC",
    "newest": "year DESC",
    "oldest": "year ASC",
    "title": "title COLLATE NOCASE ASC",
}


# ======================================================================= recommender lifecycle
def init_engine_state(app):
    app.extensions["rec_state"] = {"model": None, "dirty": True, "ts": 0.0, "lock": threading.Lock()}


def mark_dirty():
    current_app.extensions["rec_state"]["dirty"] = True


def get_engine():
    """Return the trained recommender; (re)train lazily when new ratings have arrived."""
    st = current_app.extensions["rec_state"]
    with st["lock"]:
        refit_after = current_app.config["MODEL_REFIT_SECONDS"]
        stale = st["model"] is None or (st["dirty"] and time.time() - st["ts"] >= refit_after)
        if stale:
            db = get_db()
            books = pd.read_sql_query("SELECT id AS book_id, title, author, genres, description FROM books", db)
            if books.empty:
                return None
            ratings = pd.read_sql_query("SELECT user_id, book_id, rating FROM ratings", db)
            st["model"] = HybridRecommender().fit(books, ratings)
            st["ts"], st["dirty"] = time.time(), False
    return st["model"]


# ======================================================================= books
def _like(s):
    return "%" + s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def all_genres(db):
    rows = db.execute("SELECT genres FROM books").fetchall()
    return sorted({g for r in rows for g in r["genres"].split(";") if g})


def search_books(db, q="", genre="", author="", min_rating=0.0, sort="popular", page=1, per_page=12):
    where, params = [], []
    if q:
        where.append("(title LIKE ? ESCAPE '\\' OR author LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\' OR genres LIKE ? ESCAPE '\\')")
        params += [_like(q)] * 4
    if genre:
        where.append("(';' || genres || ';') LIKE ? ESCAPE '\\'")
        params.append(_like(";" + genre + ";"))
    if author:
        where.append("author LIKE ? ESCAPE '\\'")
        params.append(_like(author))
    if min_rating:
        where.append("avg_rating >= ?")
        params.append(min_rating)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    total = db.execute(f"SELECT COUNT(*) FROM books {clause}", params).fetchone()[0]
    order = SORTS.get(sort, SORTS["popular"])
    rows = db.execute(f"SELECT * FROM books {clause} ORDER BY {order} LIMIT ? OFFSET ?",
                      params + [per_page, (max(page, 1) - 1) * per_page]).fetchall()
    return rows, total


def decorate(db, user_id, rows):
    """Turn rows into dicts and add genres list, favourite flag and the user's own rating."""
    out = [dict(r) for r in rows]
    for b in out:
        b["genre_list"] = [g for g in b["genres"].split(";") if g]
        b["is_fav"], b["my_rating"] = False, None
    if user_id and out:
        ids = [b["id"] for b in out]
        qm = ",".join("?" * len(ids))
        favs = {r[0] for r in db.execute(f"SELECT book_id FROM favorites WHERE user_id=? AND book_id IN ({qm})", [user_id] + ids)}
        mine = {r[0]: r[1] for r in db.execute(f"SELECT book_id, rating FROM ratings WHERE user_id=? AND book_id IN ({qm})", [user_id] + ids)}
        for b in out:
            b["is_fav"], b["my_rating"] = b["id"] in favs, mine.get(b["id"])
    return out


def books_by_ids(db, user_id, ids):
    if not ids:
        return []
    qm = ",".join("?" * len(ids))
    rows = {r["id"]: r for r in db.execute(f"SELECT * FROM books WHERE id IN ({qm})", ids)}
    return decorate(db, user_id, [rows[i] for i in ids if i in rows])


# ======================================================================= interactions
def log(db, user_id, book_id, action, value=None):
    db.execute("INSERT INTO interactions(user_id, book_id, action, value) VALUES (?,?,?,?)", (user_id, book_id, action, value))


def log_view(db, user_id, book_id):
    recent = db.execute("SELECT 1 FROM interactions WHERE user_id=? AND book_id=? AND action='view' "
                        "AND created_at > datetime('now','-10 minutes')", (user_id, book_id)).fetchone()
    if not recent:
        log(db, user_id, book_id, "view")
        db.commit()


def refresh_book_stats(db, book_id):
    db.execute("""UPDATE books SET
                    avg_rating = COALESCE((SELECT ROUND(AVG(rating), 2) FROM ratings WHERE book_id = books.id), 0),
                    ratings_count = (SELECT COUNT(*) FROM ratings WHERE book_id = books.id)
                  WHERE id = ?""", (book_id,))


def set_rating(db, user_id, book_id, rating):
    db.execute("""INSERT INTO ratings(user_id, book_id, rating) VALUES (?,?,?)
                  ON CONFLICT(user_id, book_id) DO UPDATE SET rating=excluded.rating, updated_at=CURRENT_TIMESTAMP""",
               (user_id, book_id, rating))
    log(db, user_id, book_id, "rate", rating)
    refresh_book_stats(db, book_id)
    db.commit()
    mark_dirty()


def remove_rating(db, user_id, book_id):
    db.execute("DELETE FROM ratings WHERE user_id=? AND book_id=?", (user_id, book_id))
    log(db, user_id, book_id, "unrate")
    refresh_book_stats(db, book_id)
    db.commit()
    mark_dirty()


def toggle_favorite(db, user_id, book_id):
    exists = db.execute("SELECT id FROM favorites WHERE user_id=? AND book_id=?", (user_id, book_id)).fetchone()
    if exists:
        db.execute("DELETE FROM favorites WHERE id=?", (exists["id"],))
        log(db, user_id, book_id, "unfavorite")
        state = False
    else:
        db.execute("INSERT INTO favorites(user_id, book_id) VALUES (?,?)", (user_id, book_id))
        log(db, user_id, book_id, "favorite")
        state = True
    db.commit()
    return state


# ======================================================================= recommendations
def model_inputs(db, user):
    """Convert a user's stored behaviour into the format the recommender expects."""
    uid = user["id"]
    inter = {r["book_id"]: float(r["rating"]) for r in db.execute("SELECT book_id, rating FROM ratings WHERE user_id=?", (uid,))}
    for r in db.execute("SELECT book_id FROM favorites WHERE user_id=?", (uid,)):
        inter[r["book_id"]] = max(inter.get(r["book_id"], 0.0), 4.0 if r["book_id"] in inter else 5.0)
    implicit = [r["book_id"] for r in db.execute(
        "SELECT DISTINCT book_id FROM interactions WHERE user_id=? AND action='view' ORDER BY id DESC LIMIT 30", (uid,))
        if r["book_id"] not in inter]
    genres = [g for g in (user["preferred_genres"] or "").split(";") if g]
    return inter, implicit, genres


def recommend_for_user(db, user, k=12, genre=None):
    model = get_engine()
    if model is None:
        return []
    inter, implicit, genres = model_inputs(db, user)
    pool = k if not genre else len(model.ids)
    recs = model.recommend(inter, genres=genres, implicit=implicit, k=pool)
    books = {b["id"]: b for b in books_by_ids(db, user["id"], [r["book_id"] for r in recs])}
    out = []
    for r in recs:
        b = books.get(r["book_id"])
        if not b or (genre and genre not in b["genre_list"]):
            continue
        b.update(reasons=r["reasons"], match_pct=r["match_pct"], components=r["components"])
        out.append(b)
        if len(out) >= k:
            break
    return out


def similar_books(db, user_id, book_id, k=6):
    model = get_engine()
    if model is None:
        return []
    sims = model.similar(book_id, k)
    books = {b["id"]: b for b in books_by_ids(db, user_id, [s["book_id"] for s in sims])}
    out = []
    for s in sims:
        if s["book_id"] in books:
            b = books[s["book_id"]]
            b["reasons"] = s["reasons"]
            out.append(b)
    return out


def taste_summary(db, user_id):
    """Top genres among books the user rated >= 4 or favourited (shown on the profile)."""
    rows = db.execute("""SELECT b.genres FROM books b WHERE b.id IN
                         (SELECT book_id FROM ratings WHERE user_id=? AND rating>=4
                          UNION SELECT book_id FROM favorites WHERE user_id=?)""", (user_id, user_id)).fetchall()
    counts = {}
    for r in rows:
        for g in r["genres"].split(";"):
            counts[g] = counts.get(g, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])[:6]
