# Phase 8: Testing

Run all automated tests: `python -m unittest discover -s tests -t . -v`  → **43 tests, all passing** (≈10 s) at the time of packaging.

## 8.1 Unit tests (ML & data) — `tests/test_recommender.py`
| ID | Test | Input | Expected | Actual |
|---|---|---|---|---|
| U1 | Returns K unique items with reasons | liked "Dune", k=8 | 8 distinct books, each with a reason | ✅ Pass |
| U2 | Never recommends rated books | rated Dune, Foundation | none of them in the list | ✅ Pass |
| U3 | Cold start, no data | `{}` | popular books, reason mentions community | ✅ Pass |
| U4 | Genre interest drives cold start | genres=["Horror"] | ≥ 4 of 6 are Horror | ✅ Pass |
| U5 | Liked sci-fi → sci-fi | 4 sci-fi books at 5★ | ≥ 5 of 8 are sci-fi **and** CF signal > 0 | ✅ Pass |
| U6 | Low ratings push genre away | horror 1★, romance 5★ | ≤ 1 horror in top 8 | ✅ Pass |
| U7 | Similar books | The Hobbit | 5 results, not itself, top result Fantasy | ✅ Pass |
| U8 | Score range | any user | 0 ≤ score ≤ 1 | ✅ Pass |
| U9 | Cleaning rules | deliberately dirty tables | duplicates merged, invalid years/ratings removed, missing values filled, sparse users dropped | ✅ Pass |
| U10 | Goodbooks layout | mini files in Goodbooks format | genres derived from tags; "to-read" ignored | ✅ Pass |
| U11 | Train/test split has no leakage | real data | train ∩ test = ∅ | ✅ Pass |
| U12 | Metrics correct | perfect and zero lists | P=NDCG=1 / all 0 | ✅ Pass |
| U13 | Hybrid beats random | 120 users | higher NDCG@10 and Precision@10 | ✅ Pass |

## 8.2 Functional tests — `tests/test_app.py`
| ID | Feature | Input | Expected | Actual |
|---|---|---|---|---|
| F1 | Register | valid data | account created, auto login, password stored hashed | ✅ Pass |
| F2 | Register validation | short username / bad email / weak password | 400 + specific message | ✅ Pass |
| F3 | Duplicate account | same username (different case) | rejected | ✅ Pass |
| F4 | Login / logout | valid credentials | success; protected pages redirect when logged out | ✅ Pass |
| F5 | Wrong password | bad password | 401 generic error | ✅ Pass |
| F6 | Brute force | 6 wrong attempts | 429 throttle | ✅ Pass |
| F7 | Open redirect | `next=//evil.com` | redirected locally | ✅ Pass |
| F8 | CSRF | POST without token | 400 | ✅ Pass |
| F9 | Pages render | `/ /books /books/1 /about /login /register` | 200 | ✅ Pass |
| F10 | Unknown book | `/books/99999` | 404 | ✅ Pass |
| F11 | Search | `q=hobbit`, `author=tolkien` | matching books | ✅ Pass |
| F12 | Filter | genre=Horror; min_rating=4 | only matching books | ✅ Pass |
| F13 | Sort + pagination | sort=title, page 2 | 5 items, alphabetical | ✅ Pass |
| F14 | Rate | rating 5 then 2 | one row, average/count updated, history logged | ✅ Pass |
| F15 | Invalid rating | 0, 6, "5", 4.5, null, true | 400 each | ✅ Pass |
| F16 | Remove rating | DELETE | rating cleared | ✅ Pass |
| F17 | Favourite toggle | POST twice | true → false; favourites page/API correct | ✅ Pass |
| F18 | View logging | open book twice | one `view` entry within 10 min | ✅ Pass |
| F19 | Profile update | genres Horror;Romance | saved | ✅ Pass |
| F20 | API requires login | rate without session | 401 | ✅ Pass |

## 8.3 Security tests
| ID | Attack | Expected | Actual |
|---|---|---|---|
| S1 | SQL injection in search `' OR 1=1; DROP TABLE books;--` | no results, table intact | ✅ Pass |
| S2 | XSS `<script>` in search | output escaped | ✅ Pass |
| S3 | Seed accounts login | impossible | ✅ Pass |

## 8.4 Integration & recommendation tests (register → interact → recommend)
| ID | Scenario | Expected | Actual |
|---|---|---|---|
| I1 | New user picks Horror | ≥ 3 of 6 recommendations are Horror, each with reason and 0–100 % match | ✅ Pass |
| I2 | User rates 4 Romance books 5★ | rated books excluded; ≥ 4 of 10 are Romance | ✅ Pass |
| I3 | User favourites 4 Horror books | ≥ 3 of 8 Horror | ✅ Pass |
| I4 | `/recommendations` page + genre filter | page shows match % and 💡; filter returns only that genre | ✅ Pass |
| I5 | `/api/books/1/similar` | 6 books, not itself | ✅ Pass |
| I6 | Recommendations without login | 401 / redirect | ✅ Pass |

Live end-to-end check (real HTTP server, demo user): cold start → *Foundation* "Matches your interest in Science Fiction". After rating four biographies 5★ → top picks
*Wings of Fire* ("Similar to *Becoming*, which you liked") and *Long Walk to Freedom*.

## 8.5 Offline accuracy evaluation
See `docs/02_dataset_and_ml.md` §4.6 (`python -m ml.evaluate`).

## 8.6 Manual UI checklist (please tick these yourself before the demo — not executed by the build process)
- [ ] Layout on a phone-width window (≤ 480 px): menu button works, cards in 2 columns
- [ ] Star widget: hover preview, click saves, "Clear rating" works
- [ ] Heart button on cards toggles without page reload and shows a toast
- [ ] Flash messages for errors/success are readable
- [ ] Keyboard navigation (Tab) shows focus outlines
