"""JSON REST API  (documented in docs/03_api.md).  All POST/DELETE calls need the X-CSRF-Token header."""
from flask import Blueprint, g, jsonify, request
from .db import get_db
from .security import login_required
from . import services as svc

bp = Blueprint("api", __name__, url_prefix="/api")


def _book_json(b):
    keys = ["id", "title", "author", "year", "genre_list", "description", "cover_url", "avg_rating", "ratings_count",
            "is_fav", "my_rating", "reasons", "match_pct", "components"]
    out = {k: b[k] for k in keys if k in b}
    if "genre_list" in out:
        out["genres"] = out.pop("genre_list")
    return out


def _uid():
    return g.user["id"] if g.user else None


def _book_or_404(db, book_id):
    return db.execute("SELECT id FROM books WHERE id=?", (book_id,)).fetchone()


@bp.get("/genres")
def genres():
    return jsonify(genres=svc.all_genres(get_db()))


@bp.get("/books")
def list_books():
    db = get_db()
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per = min(max(int(request.args.get("per_page", 12)), 1), 50)
        min_rating = float(request.args.get("min_rating", 0) or 0)
    except ValueError:
        return jsonify(error="page, per_page and min_rating must be numbers"), 400
    rows, total = svc.search_books(db, q=request.args.get("q", "").strip()[:100], genre=request.args.get("genre", ""),
                                   author=request.args.get("author", "").strip()[:100], min_rating=min_rating,
                                   sort=request.args.get("sort", "popular"), page=page, per_page=per)
    return jsonify(total=total, page=page, per_page=per, books=[_book_json(b) for b in svc.decorate(db, _uid(), rows)])


@bp.get("/books/<int:book_id>")
def get_book(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if row is None:
        return jsonify(error="Book not found"), 404
    return jsonify(_book_json(svc.decorate(db, _uid(), [row])[0]))


@bp.get("/books/<int:book_id>/similar")
def similar(book_id):
    db = get_db()
    if not _book_or_404(db, book_id):
        return jsonify(error="Book not found"), 404
    return jsonify(similar=[_book_json(b) for b in svc.similar_books(db, _uid(), book_id, 6)])


@bp.post("/books/<int:book_id>/rate")
@login_required
def rate(book_id):
    db = get_db()
    if not _book_or_404(db, book_id):
        return jsonify(error="Book not found"), 404
    data = request.get_json(silent=True) or {}
    value = data.get("rating")
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        return jsonify(error="rating must be an integer between 1 and 5"), 400
    svc.set_rating(db, g.user["id"], book_id, value)
    b = db.execute("SELECT avg_rating, ratings_count FROM books WHERE id=?", (book_id,)).fetchone()
    return jsonify(ok=True, my_rating=value, avg_rating=b["avg_rating"], ratings_count=b["ratings_count"])


@bp.delete("/books/<int:book_id>/rate")
@login_required
def unrate(book_id):
    db = get_db()
    if not _book_or_404(db, book_id):
        return jsonify(error="Book not found"), 404
    svc.remove_rating(db, g.user["id"], book_id)
    b = db.execute("SELECT avg_rating, ratings_count FROM books WHERE id=?", (book_id,)).fetchone()
    return jsonify(ok=True, my_rating=None, avg_rating=b["avg_rating"], ratings_count=b["ratings_count"])


@bp.post("/books/<int:book_id>/favorite")
@login_required
def favorite(book_id):
    db = get_db()
    if not _book_or_404(db, book_id):
        return jsonify(error="Book not found"), 404
    return jsonify(ok=True, favorite=svc.toggle_favorite(db, g.user["id"], book_id))


@bp.get("/recommendations")
@login_required
def recommendations():
    try:
        k = min(max(int(request.args.get("k", 10)), 1), 50)
    except ValueError:
        return jsonify(error="k must be a number"), 400
    recs = svc.recommend_for_user(get_db(), g.user, k=k, genre=request.args.get("genre") or None)
    return jsonify(count=len(recs), recommendations=[_book_json(b) for b in recs])


@bp.get("/me/favorites")
@login_required
def my_favorites():
    db = get_db()
    rows = db.execute("SELECT b.* FROM books b JOIN favorites f ON f.book_id=b.id WHERE f.user_id=? ORDER BY f.created_at DESC",
                      (g.user["id"],)).fetchall()
    return jsonify(favorites=[_book_json(b) for b in svc.decorate(db, g.user["id"], rows)])


@bp.get("/me/history")
@login_required
def my_history():
    rows = get_db().execute("""SELECT i.action, i.value, i.created_at, b.id AS book_id, b.title FROM interactions i
                               JOIN books b ON b.id=i.book_id WHERE i.user_id=? ORDER BY i.id DESC LIMIT 100""",
                            (g.user["id"],)).fetchall()
    return jsonify(history=[dict(r) for r in rows])
