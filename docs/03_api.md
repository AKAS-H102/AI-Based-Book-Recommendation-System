# REST API Documentation

Base URL `http://127.0.0.1:5000`. Responses are JSON. Authentication uses the session cookie set by `/login` (browser) — log in through the web form first.
**CSRF:** every `POST`/`DELETE` must send the header `X-CSRF-Token: <token>` (the token is in `<meta name="csrf-token">` of every page; `static/js/main.js` does this automatically).
Errors: `{"error": "message"}` with status 400 (bad input / CSRF), 401 (login required), 404 (not found).

## Book endpoints (public)
| Method | Path | Description |
|---|---|---|
| GET | `/api/genres` | List of all genres |
| GET | `/api/books` | Search/filter/sort/paginate |
| GET | `/api/books/<id>` | One book |
| GET | `/api/books/<id>/similar` | 6 similar books with reasons |

**`GET /api/books` query parameters** (the response below is an illustrative example): `q` (keyword in title/author/description/genre), `genre`, `author`, `min_rating` (0–5), `sort` (`popular` | `rating` | `newest` | `oldest` | `title`), `page` (≥1), `per_page` (1–50, default 12).
```json
{ "total": 11, "page": 1, "per_page": 12,
  "books": [ { "id": 1, "title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937,
               "genres": ["Fantasy", "Adventure"], "description": "A comfortable hobbit …", "cover_url": "",
               "avg_rating": 3.9, "ratings_count": 112, "is_fav": false, "my_rating": null } ] }
```
(`is_fav`/`my_rating` are filled only when logged in.)

## User endpoints (login required)
| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/api/books/<id>/rate` | `{"rating": 1-5}` (integer) | Create/update the user's rating |
| DELETE | `/api/books/<id>/rate` | – | Remove the user's rating |
| POST | `/api/books/<id>/favorite` | – | Toggle favourite → `{"favorite": true/false}` |
| GET | `/api/recommendations?k=10&genre=Mystery` | – | Personalised top-K (k 1–50), optional genre filter |
| GET | `/api/me/favorites` | – | The user's favourites |
| GET | `/api/me/history` | – | Last 100 interactions |

Rate response: `{"ok": true, "my_rating": 5, "avg_rating": 4.01, "ratings_count": 113}`

Recommendation item (book fields plus):
```json
{ "match_pct": 69,
  "components": {"content": 0.266, "collaborative": 0.12, "popularity": 0.186},
  "reasons": ["Similar to \"Becoming\", which you liked (shared genres: Biography, Non-Fiction)"] }
```

## Page routes (HTML)
`/` home · `/books` list · `/books/<id>` detail · `/recommendations` · `/favorites` · `/history` · `/profile` · `/about` · `/register` · `/login` · `POST /logout`.

## Security notes
Passwords hashed (Werkzeug scrypt/PBKDF2, salted) · parameterised SQL everywhere (no string-built values; `ORDER BY` uses a whitelist) · Jinja auto-escaping (XSS) ·
CSRF token on all state-changing requests · session cookie `HttpOnly` + `SameSite=Lax` · session reset on login (fixation) · `next=` redirect restricted to local paths ·
login throttling (5 failures / 5 min per user+IP) · input validation (length, type, range) · security headers · generic login error message (no user enumeration).
