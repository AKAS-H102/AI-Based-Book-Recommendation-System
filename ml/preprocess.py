"""
Data cleaning & preprocessing pipeline.

Input  : data/raw/books.csv, data/raw/ratings.csv   (sample format OR Goodbooks-10k format)
Output : data/processed/books_clean.csv, data/processed/ratings_clean.csv

Steps (each is reported when the script runs):
 1. Normalise column names / whitespace
 2. Handle missing titles, authors, years, descriptions, genres
 3. Remove duplicate books (same title + author) and re-map their ratings
 4. Validate ratings (1-5), drop duplicate (user, book) pairs, drop orphan ratings
 5. Drop users with too few ratings (not enough signal)
 6. Goodbooks-10k only: derive genres from tags.csv + book_tags.csv

Run:  python -m ml.preprocess            (uses data/raw)
      python -m ml.preprocess --raw path/to/goodbooks --max-users 5000
"""
import argparse
import datetime
import os
import re
import pandas as pd

GENRE_TAGS = {  # tag name in Goodbooks-10k  ->  clean genre name
    "fantasy": "Fantasy", "science-fiction": "Science Fiction", "sci-fi": "Science Fiction",
    "mystery": "Mystery", "thriller": "Thriller", "romance": "Romance",
    "historical-fiction": "Historical Fiction", "non-fiction": "Non-Fiction", "nonfiction": "Non-Fiction",
    "self-help": "Self-Help", "biography": "Biography", "classics": "Classics", "horror": "Horror",
    "young-adult": "Young Adult", "dystopian": "Dystopian", "dystopia": "Dystopian",
    "adventure": "Adventure", "history": "History", "science": "Science", "memoir": "Biography",
}


def _squash(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def _clean_genres(value):
    if pd.isna(value) or not str(value).strip():
        return "General"
    parts = re.split(r"[;,|]", str(value))
    seen, out = set(), []
    for p in parts:
        p = _squash(p).title().replace("Non-Fiction", "Non-Fiction")
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return ";".join(out) or "General"


def _genres_from_tags(raw_dir, books):
    tags_f, bt_f = os.path.join(raw_dir, "tags.csv"), os.path.join(raw_dir, "book_tags.csv")
    if not (os.path.exists(tags_f) and os.path.exists(bt_f)) or "goodreads_book_id" not in books.columns:
        return books
    tags, bt = pd.read_csv(tags_f), pd.read_csv(bt_f)
    bt = bt.merge(tags, on="tag_id")
    bt["genre"] = bt["tag_name"].map(GENRE_TAGS)
    g = bt.dropna(subset=["genre"]).sort_values("count", ascending=False)
    g = g.groupby("goodreads_book_id")["genre"].apply(lambda s: ";".join(list(dict.fromkeys(s))[:3]))
    top = bt.sort_values("count", ascending=False).groupby("goodreads_book_id")["tag_name"].apply(
        lambda s: " ".join(s.head(15)).replace("-", " "))
    books = books.copy()
    books["genres"] = books["goodreads_book_id"].map(g)
    books["description"] = books["goodreads_book_id"].map(top)   # Goodbooks has no description -> use top tags
    return books


def clean(books, ratings, min_user_ratings=3, raw_dir=None, max_users=None, seed=42):
    rep = {"raw_books": len(books), "raw_ratings": len(ratings)}
    books = books.copy()
    books.columns = [c.strip().lower() for c in books.columns]
    if raw_dir:
        books = _genres_from_tags(raw_dir, books)
    books = books.rename(columns={"authors": "author", "original_publication_year": "year", "image_url": "cover_url"})
    for col in ["title", "author", "year", "genres", "description", "cover_url"]:
        if col not in books.columns:
            books[col] = None
    if "original_title" in books.columns:                       # prefer title, fall back to original_title
        books["title"] = books["title"].fillna(books["original_title"])

    # 1-2. whitespace + missing values -------------------------------------------------
    for col in ["title", "author", "description", "cover_url"]:
        books[col] = books[col].apply(lambda v: _squash(v) if pd.notna(v) else None)
    rep["missing_titles_dropped"] = int(books["title"].isna().sum() + (books["title"] == "").sum())
    books = books[books["title"].notna() & (books["title"] != "")]
    rep["missing_authors_filled"] = int(books["author"].isna().sum())
    books["author"] = books["author"].fillna("Unknown")
    books["genres"] = books["genres"].apply(_clean_genres)
    year = pd.to_numeric(books["year"], errors="coerce")
    bad_year = year.notna() & ((year < 1000) | (year > datetime.date.today().year))
    rep["invalid_or_missing_years"] = int(year.isna().sum() + bad_year.sum())
    books["year"] = year.mask(bad_year).round().astype("Int64")
    missing_desc = books["description"].isna() | (books["description"] == "")
    rep["missing_descriptions_filled"] = int(missing_desc.sum())
    books.loc[missing_desc, "description"] = books.loc[missing_desc, "genres"].str.replace(";", " ") + " book"
    books["cover_url"] = books["cover_url"].fillna("")

    # 3. duplicates --------------------------------------------------------------------
    books["_key"] = books["title"].str.lower() + "|" + books["author"].str.lower()
    keep_id = books.groupby("_key")["book_id"].transform("first")
    id_map = dict(zip(books["book_id"], keep_id))
    rep["duplicate_books_removed"] = int((books["book_id"] != keep_id).sum())
    books = books[books["book_id"] == keep_id].drop(columns="_key")
    books = books[["book_id", "title", "author", "year", "genres", "description", "cover_url"]]

    # 4. ratings -----------------------------------------------------------------------
    ratings = ratings[["user_id", "book_id", "rating"]].copy()
    ratings["rating"] = pd.to_numeric(ratings["rating"], errors="coerce")
    ratings = ratings.dropna()
    rep["invalid_ratings_removed"] = int(rep["raw_ratings"] - len(ratings) + (~ratings["rating"].between(1, 5)).sum())
    ratings = ratings[ratings["rating"].between(1, 5)]
    ratings["book_id"] = ratings["book_id"].map(id_map)
    ratings = ratings.dropna(subset=["book_id"])                  # orphan ratings
    before = len(ratings)
    ratings = ratings.drop_duplicates(["user_id", "book_id"], keep="last")
    rep["duplicate_ratings_removed"] = before - len(ratings)
    # 5. sparse users
    counts = ratings.groupby("user_id")["book_id"].transform("count")
    rep["users_dropped_too_few_ratings"] = int(ratings.loc[counts < min_user_ratings, "user_id"].nunique())
    ratings = ratings[counts >= min_user_ratings].astype({"user_id": int, "book_id": int, "rating": int})
    if max_users and ratings["user_id"].nunique() > max_users:      # keep the project laptop-friendly
        keep = pd.Series(ratings["user_id"].unique()).sample(max_users, random_state=seed)
        ratings = ratings[ratings["user_id"].isin(keep)]
        rep["users_sampled_to"] = max_users
    rep.update(clean_books=len(books), clean_ratings=len(ratings), clean_users=ratings["user_id"].nunique())
    return books.reset_index(drop=True), ratings.reset_index(drop=True), rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--max-users", type=int, default=None, help="randomly keep only this many users (use ~5000 for Goodbooks-10k)")
    a = ap.parse_args()
    books = pd.read_csv(os.path.join(a.raw, "books.csv"))
    ratings = pd.read_csv(os.path.join(a.raw, "ratings.csv"))
    b, r, rep = clean(books, ratings, raw_dir=a.raw, max_users=a.max_users)
    os.makedirs(a.out, exist_ok=True)
    b.to_csv(os.path.join(a.out, "books_clean.csv"), index=False)
    r.to_csv(os.path.join(a.out, "ratings_clean.csv"), index=False)
    print("Cleaning report:")
    for k, v in rep.items():
        print(f"  {k:32s} {v}")


if __name__ == "__main__":
    main()
