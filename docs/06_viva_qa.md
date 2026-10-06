# Phase 11: Viva Preparation

## The 60-second explanation
"My system recommends books by combining three signals. **Content-based**: each book is converted to numbers using TF-IDF from its genre, author and description, and I find books similar to what you liked.
**Collaborative**: if people who liked book A also liked book B, B is recommended to you. **Popularity**: a fair average rating for new users. The weights adapt: new users get genre- and popularity-based picks,
users with more ratings get more collaborative filtering. Each recommendation shows a reason. I evaluated it by hiding 20% of each user's ratings and checking whether the model finds them."

## Core questions
**Why this project?** Choosing a book is a real information-overload problem; recommenders are widely used in industry; the project covers the full stack — data, ML, backend, database, frontend, testing.

**Why AI/ML?** Rules like "show fantasy to fantasy fans" cannot capture individual taste or hidden patterns (e.g. fans of A tend to like B). ML learns these patterns from data and improves with more feedback.

**Why this algorithm (hybrid)?** Content-only over-specialises and ignores other readers; collaborative-only fails for new users/books (cold start); popularity-only is not personal. A hybrid covers each weakness and keeps explainability.
I chose item-based CF over matrix factorisation because it is easy to explain and gives natural reasons.

**How does the recommendation system work?** (1) Convert user actions to weights: 5★ = +2 … 1★ = −2. (2) Build a taste profile from TF-IDF vectors of those books. (3) Score all unread books by content similarity, item-based CF and popularity.
(4) Combine with adaptive weights. (5) Remove already-read books, sort, show top K with reasons.

**What dataset was used?** Recommended: Goodbooks-10k (10k books, ~6M ratings, ~53k users; Zając). The bundled demo uses 99 real books with synthetic ratings from 400 imaginary readers so it runs offline — I state this clearly. *(Answer for your own final dataset.)*

**How was the data preprocessed?** Trimmed whitespace; filled missing authors/descriptions/genres; invalid years set to missing; removed duplicate books and re-mapped their ratings; removed invalid and duplicate ratings; dropped users with < 3 ratings; derived genres from tags (Goodbooks). `python -m ml.preprocess` prints a report.

**How are recommendations generated?** See the algorithm above; code in `ml/engine.py` → `HybridRecommender.recommend`.

**How is the model evaluated?** Hold-out: 80% of each user's ratings train, 20% test. Recommend top-10; hit if the user rated the hidden book ≥ 4. Metrics: Precision@10, Recall@10, NDCG@10, HitRate@10, Coverage. Compared with random, popularity, content-only, CF-only.

**What are the limitations?** Synthetic demo ratings; TF-IDF has no semantic understanding; popularity bias / filter bubble; recompute per request (fine for small data); offline metrics ≠ real satisfaction; no password reset.

**Future enhancements?** SVD/ALS or neural embeddings, diversity re-ranking, real descriptions/covers via open APIs, admin panel, A/B testing, Docker deployment.

## Technical follow-ups
**What is TF-IDF?** Term Frequency × Inverse Document Frequency. A word scores high if it is frequent in this book but rare across the catalogue, so distinctive words matter more than "the".

**What is cosine similarity?** The cosine of the angle between two vectors: 1 = same direction (very similar), 0 = unrelated. It ignores vector length, so a long and a short description can still match.

**What is collaborative filtering? Item-based vs user-based?** Uses other users' behaviour. Item-based compares books by who rated them similarly; user-based compares users. Item-based is more stable and easier to explain (similarities change slowly).

**Why subtract each user's average rating?** Some readers rate everything high, others low. Centring compares *relative* preference ("liked more than usual") rather than absolute scores (adjusted cosine similarity).

**What is the cold-start problem and how did you handle it?** A new user/book has no history. New users pick genres at sign-up (content profile) and get popularity-weighted results; CF weight grows as `min(1, interactions/8)`. New *books* are still recommendable through content features.

**What is "significance weighting"?** Two books co-rated by only 2 users can look perfectly similar by chance. I scale similarity by `min(co-raters, 20)/20`.

**Why use `rating − 3`?** 3★ is neutral; ratings above add preference, below subtract it, so disliked books push similar ones down.

**What does "match %" mean?** The normalised final score ×100, a relative ranking score — not a probability.

**What is NDCG?** Normalised Discounted Cumulative Gain — rewards putting relevant items near the top (position matters), normalised to 0–1.

**Precision vs recall?** Precision = fraction of shown items that are relevant; recall = fraction of all relevant items that were shown.

**Your hybrid is not much better than CF-only. Why keep it?** True on this data. The hybrid gives cold-start support, wider coverage (popularity-only recommends 19 % of the catalogue) and explanations. Honest reporting of this is part of the evaluation.

**Isn't synthetic data cheating?** It only proves the pipeline works and makes demos reproducible; I state it openly, and the pipeline supports a real dataset. *(Run Goodbooks-10k and report those numbers.)*

**How do you avoid data leakage in evaluation?** The test ratings are removed from the model's training data and from the user's input history; a unit test checks train ∩ test = ∅.

**How do user interactions improve recommendations?** Ratings/favourites are stored, passed as the user's profile at every request (instant effect), and added to the community rating matrix, which is retrained lazily.

**How is security handled?** Hashed salted passwords, parameterised SQL (no SQL injection), template auto-escaping (XSS), CSRF tokens, HttpOnly/SameSite cookies, login throttling, input validation, safe redirects.

**Why SQLite / Flask instead of MySQL / Django?** Zero installation and a single-file database make the project easy to run and demo; the same SQL and structure would port to MySQL/PostgreSQL. Flask keeps the code small enough to explain fully.

**Can it scale?** Sparse matrices handle tens of thousands of users; for millions you'd precompute item-item neighbours, use approximate nearest neighbours, a task queue for retraining and a server database.

**What is the filter-bubble problem?** Recommending only what matches past taste narrows exposure. Mitigation: diversity/novelty re-ranking (future work).

**Which library does what?** pandas = data tables; NumPy/SciPy = fast numeric/sparse maths; scikit-learn = TF-IDF; Flask = web server; SQLite = database.

## Be ready to demo
Show: `python -m ml.preprocess` report · `python -m ml.evaluate` table · live signup → rate → recommendation change · `python -m unittest discover -s tests -t .`
