"""Page routes (server-rendered HTML)."""
import math
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from .db import get_db
from .security import login_required
from . import services as svc

bp = Blueprint("main", __name__)


def _float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _int(v, default=1):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@bp.route("/")
def home():
    db = get_db()
    uid = g.user["id"] if g.user else None
    top = svc.decorate(db, uid, db.execute(
        "SELECT * FROM books WHERE ratings_count >= 10 ORDER BY avg_rating DESC, ratings_count DESC LIMIT 8").fetchall())
    recs = svc.recommend_for_user(db, g.user, k=4) if g.user else []
    stats = {"books": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
             "ratings": db.execute("SELECT COUNT(*) FROM ratings").fetchone()[0],
             "readers": db.execute("SELECT COUNT(*) FROM users").fetchone()[0]}
    return render_template("index.html", top=top, recs=recs, stats=stats, genres=svc.all_genres(db))


@bp.route("/books")
def books():
    db = get_db()
    uid = g.user["id"] if g.user else None
    f = {"q": request.args.get("q", "").strip()[:100], "genre": request.args.get("genre", "").strip(),
         "author": request.args.get("author", "").strip()[:100], "min_rating": _float(request.args.get("min_rating")),
         "sort": request.args.get("sort", "popular")}
    page = max(_int(request.args.get("page"), 1), 1)
    per = current_app.config["BOOKS_PER_PAGE"]
    rows, total = svc.search_books(db, page=page, per_page=per, **f)
    return render_template("books.html", books=svc.decorate(db, uid, rows), total=total, page=page,
                           pages=max(1, math.ceil(total / per)), f=f, genres=svc.all_genres(db))


@bp.route("/books/<int:book_id>")
def book_detail(book_id):
    db = get_db()
    row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if row is None:
        abort(404)
    uid = g.user["id"] if g.user else None
    book = svc.decorate(db, uid, [row])[0]
    if g.user:
        svc.log_view(db, uid, book_id)
    dist = {r["rating"]: r["n"] for r in db.execute(
        "SELECT rating, COUNT(*) n FROM ratings WHERE book_id=? GROUP BY rating", (book_id,))}
    return render_template("book_detail.html", book=book, similar=svc.similar_books(db, uid, book_id, 6),
                           dist=[dist.get(i, 0) for i in range(5, 0, -1)])


@bp.route("/recommendations")
@login_required
def recommendations():
    db = get_db()
    genre = request.args.get("genre", "").strip() or None
    recs = svc.recommend_for_user(db, g.user, k=18, genre=genre)
    n_rated = db.execute("SELECT COUNT(*) FROM ratings WHERE user_id=?", (g.user["id"],)).fetchone()[0]
    n_fav = db.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?", (g.user["id"],)).fetchone()[0]
    return render_template("recommendations.html", recs=recs, genre=genre, genres=svc.all_genres(db),
                           n_rated=n_rated, n_fav=n_fav)


@bp.route("/favorites")
@login_required
def favorites():
    db = get_db()
    rows = db.execute("SELECT b.* FROM books b JOIN favorites f ON f.book_id=b.id WHERE f.user_id=? "
                      "ORDER BY f.created_at DESC", (g.user["id"],)).fetchall()
    return render_template("favorites.html", books=svc.decorate(db, g.user["id"], rows))


@bp.route("/history")
@login_required
def history():
    db = get_db()
    uid = g.user["id"]
    rated = db.execute("""SELECT b.*, r.rating AS my_rating_value, r.updated_at FROM ratings r
                          JOIN books b ON b.id=r.book_id WHERE r.user_id=? ORDER BY r.updated_at DESC""", (uid,)).fetchall()
    timeline = db.execute("""SELECT i.action, i.value, i.created_at, b.id AS book_id, b.title FROM interactions i
                             JOIN books b ON b.id=i.book_id WHERE i.user_id=? ORDER BY i.id DESC LIMIT 60""", (uid,)).fetchall()
    return render_template("history.html", rated=svc.decorate(db, uid, rated), timeline=timeline)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    genres = svc.all_genres(db)
    uid = g.user["id"]
    if request.method == "POST":
        chosen = [x for x in request.form.getlist("genres") if x in genres]
        db.execute("UPDATE users SET full_name=?, bio=?, preferred_genres=? WHERE id=?",
                   (request.form.get("full_name", "").strip()[:80], request.form.get("bio", "").strip()[:300],
                    ";".join(chosen), uid))
        db.commit()
        flash("Profile updated. Your recommendations will reflect your new interests.", "success")
        return redirect(url_for("main.profile"))
    stats = {
        "rated": db.execute("SELECT COUNT(*) FROM ratings WHERE user_id=?", (uid,)).fetchone()[0],
        "favs": db.execute("SELECT COUNT(*) FROM favorites WHERE user_id=?", (uid,)).fetchone()[0],
        "avg": db.execute("SELECT ROUND(AVG(rating),2) FROM ratings WHERE user_id=?", (uid,)).fetchone()[0],
        "views": db.execute("SELECT COUNT(*) FROM interactions WHERE user_id=? AND action='view'", (uid,)).fetchone()[0]}
    mine = [x for x in (g.user["preferred_genres"] or "").split(";") if x]
    return render_template("profile.html", genres=genres, mine=mine, stats=stats, taste=svc.taste_summary(db, uid))


@bp.route("/about")
def about():
    return render_template("about.html")


def register_error_handlers(app):
    from flask import jsonify

    def handler(code, title):
        def _h(e):
            if request.path.startswith("/api/"):
                return jsonify(error=getattr(e, "description", title)), code
            return render_template("error.html", code=code, title=title,
                                   message=getattr(e, "description", "")), code
        return _h
    for code, title in [(400, "Bad request"), (404, "Page not found"), (405, "Method not allowed"), (500, "Something went wrong")]:
        app.register_error_handler(code, handler(code, title))
