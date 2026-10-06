PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    username         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash    TEXT NOT NULL,
    full_name        TEXT DEFAULT '',
    bio              TEXT DEFAULT '',
    preferred_genres TEXT DEFAULT '',            -- ';' separated, used for cold start
    is_seed          INTEGER DEFAULT 0,          -- 1 = imported demo reader
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books (
    id            INTEGER PRIMARY KEY,
    title         TEXT NOT NULL,
    author        TEXT NOT NULL,
    year          INTEGER,
    genres        TEXT NOT NULL,                 -- ';' separated
    description   TEXT,
    cover_url     TEXT DEFAULT '',
    avg_rating    REAL DEFAULT 0,
    ratings_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ratings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id    INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, book_id)
);

CREATE TABLE IF NOT EXISTS favorites (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id    INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, book_id)
);

CREATE TABLE IF NOT EXISTS interactions (       -- full history log
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id    INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    action     TEXT NOT NULL CHECK (action IN ('view','rate','unrate','favorite','unfavorite')),
    value      REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ratings_book  ON ratings(book_id);
CREATE INDEX IF NOT EXISTS idx_ratings_user  ON ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_fav_user      ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_inter_user    ON interactions(user_id, created_at);
