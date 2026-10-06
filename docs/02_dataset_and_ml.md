# Phase 4: Dataset & Machine Learning

## 4.1 Dataset
### Recommended public dataset: **Goodbooks-10k**
* Source: Zygmunt Zając, *goodbooks-10k* — https://github.com/zygmuntz/goodbooks-10k (data collected from Goodreads). Also on Kaggle. **Check the licence in the repository and cite it.**
* Size: 10,000 books, about 6 million ratings from about 53,000 users (ratings 1–5).
* Files used: `books.csv`, `ratings.csv`, `tags.csv`, `book_tags.csv`.

| File | Important columns |
|---|---|
| books.csv | `book_id`, `goodreads_book_id`, `title`, `authors`, `original_publication_year`, `average_rating`, `ratings_count`, `image_url`, `language_code` |
| ratings.csv | `user_id`, `book_id`, `rating` |
| tags.csv | `tag_id`, `tag_name` |
| book_tags.csv | `goodreads_book_id`, `tag_id`, `count` (how many users applied the tag) |

Goodbooks-10k has **no description or genre column**. `ml/preprocess.py` therefore derives *genres* from the most-used tags that match a genre
whitelist (fantasy, mystery, romance, …), and uses the top tags as the text "description" for TF-IDF.
**Alternative:** *Book-Crossing* (Ziegler et al., 2004; ratings 0–10, much messier data — good if you want a bigger cleaning story).

### Use it (3 steps)
```bash
# 1. Download goodbooks-10k, put books.csv, ratings.csv, tags.csv, book_tags.csv in  data/raw/   (replace the sample files)
python -m ml.preprocess --max-users 5000      # 5000 users keeps everything fast on a laptop
python -m ml.evaluate                         # your real numbers for the report
python scripts/init_db.py --reset && python run.py
```
> Status: the Goodbooks loader is covered by a unit test on a miniature file set in the same format, but was **not** run on the full download
> in the build environment (no internet). Run it once and fix any column-name differences if your copy differs.

### Included sample dataset (for offline demo)
`ml/make_sample_data.py` — 99 real, famous books (title, author, year, genres, short *original* description) and **synthetic** ratings from
400 imaginary readers (each has 2–3 liked genres, 2 disliked genres; ratings = taste + book quality + noise). It is **not real user data**;
results on it show that the pipeline works, not how it performs on real readers.

## 4.2 Data cleaning & preprocessing (`ml/preprocess.py`)
| Problem | How it is handled |
|---|---|
| Whitespace / inconsistent case | collapse spaces; title-case genres |
| Missing title | drop the row (cannot display) |
| Missing author | fill with "Unknown" |
| Missing / impossible year (<1000 or > current year) | set to missing (shown blank) |
| Missing description | generate from genres (so TF-IDF still has text) |
| Missing genre | fill with "General" |
| Duplicate books (same title + author, case-insensitive) | keep first; **re-map their ratings** to the kept ID |
| Invalid ratings (outside 1–5, non-numeric) | drop |
| Duplicate (user, book) ratings | keep the latest |
| Ratings for unknown books | drop (orphans) |
| Users with < 3 ratings | drop (not enough signal) |
The script prints a cleaning report with counts for each step (use it in the report). The unit test `test_cleaning_handles_dirty_data` proves every rule on a deliberately dirty table.

## 4.3 Feature extraction
**Content features.** For each book build one text: *description + genres (repeated ×3) + author (×2) + title*. Genre/author are turned into single tokens
(`science_fiction`, `j_r_r_tolkien`). `TfidfVectorizer(stop_words='english', sublinear_tf=True, ngram_range=(1,2))` converts the text into a sparse numeric vector.
*TF-IDF idea:* a word is important if it is frequent in this book but rare across all books.

**Collaborative features.** Build an items × users matrix of ratings; subtract each user's mean rating (so a generous rater's 4 and a harsh rater's 4 mean different things); L2-normalise each item vector.
The dot-product of two normalised item vectors = *adjusted cosine similarity* (how similarly two books are rated by the same people).
Similarities are multiplied by `min(co_raters, 20)/20` ("significance weighting") so two books co-rated by only 2 people are not trusted.

**Popularity feature.** Bayesian weighted rating `WR = v/(v+m)·R + m/(v+m)·C` (v = number of ratings, R = book mean, C = global mean, m = median count) so a 5★ book with 2 votes does not beat a 4.5★ book with 2000 votes. Scaled to 0–1.

## 4.4 Choosing the algorithm
| Approach | Idea | Pros | Cons for this project |
|---|---|---|---|
| Content-based | recommend books similar to what the user liked | works for new books; very explainable; no other users needed | over-specialises (more of the same); needs good metadata |
| Collaborative (item-based) | books rated similarly by the same people | finds surprising, taste-based matches; no metadata needed | **cold-start** (new user/book); sparse data |
| Popularity | top-rated overall | trivial, strong baseline | not personal |
| **Hybrid (chosen)** | weighted combination | covers each method's weakness; explainable | slightly more code |

**Why hybrid:** the system must handle brand-new users (genre + popularity), improve as data arrives (CF), and explain results (content/CF reasons).
Item-based CF was chosen over matrix factorisation (SVD) because it is much easier to explain in a viva ("people who liked A also liked B") and gives natural explanations.

## 4.5 The recommendation algorithm (step by step)
```
Input : user's ratings/favourites (favourite = 5★ if unrated), viewed books, chosen genres
1. rating weights  w = rating − 3        (5★ → +2, 3★ → 0, 1★ → −2)  → disliked books push similar books DOWN
2. CONTENT score   profile = Σ w·tfidf(book) + 0.5·Σ tfidf(viewed) + 2·tfidf(chosen genres)
                   content(b) = cosine(profile, tfidf(b))
3. CF score        cf(b) = Σ w_i · sim(i, b) / (Σ |sim(i, b)| + 1)     over the user's rated books i
4. POP score       weighted rating, scaled 0–1
5. Scale each of the three scores to 0–1
6. Adaptive weights:  conf = min(1, n_interactions / 8)
                      w_content = 0.45 (0 if no profile)   w_cf = 0.40 × conf   w_pop = 0.15 × (1 + 2(1 − conf))   → normalised to sum 1
7. final = w_content·content + w_cf·cf + w_pop·pop ;  remove books already rated ;  return top-K
8. Explain: for each result, pick the 2 largest weighted components and show a reason
   (content → "Similar to X which you liked (shared genres …)"; cf → "Readers who liked X also liked this";
    popularity → "Highly rated by the community (4.1★ from 120 ratings)")
```
"Match %" = the final score × 100. It is a relative score for ranking, **not** a probability.

## 4.6 Evaluation
**Method (hold-out):** for each user hide 20% of their ratings; train on the rest; recommend Top-10; a hit = the user rated a hidden book ≥ 4.
**Metrics:** Precision@K (share of recommendations that are relevant), Recall@K (share of relevant books found), **NDCG@K** (rewards putting hits near the top), HitRate@K (users with ≥ 1 hit), Coverage (share of catalogue ever recommended).

**Results on the included sample data (300 users, K = 10, seed 42):**
| Model | Precision@10 | Recall@10 | NDCG@10 | HitRate@10 | Coverage |
|---|---|---|---|---|---|
| Random | 0.026 | 0.112 | 0.059 | 0.230 | 1.00 |
| Popularity only | 0.046 | 0.211 | 0.118 | 0.377 | **0.19** |
| Content-based only | 0.037 | 0.165 | 0.101 | 0.323 | 1.00 |
| Collaborative only | 0.048 | 0.221 | 0.131 | 0.387 | 1.00 |
| **Hybrid (proposed)** | 0.048 | 0.215 | 0.127 | 0.383 | 1.00 |

**Honest interpretation**
* Every model beats Random; the hybrid roughly **doubles Random's NDCG** (0.127 vs 0.059).
* The hybrid is **not clearly better than CF-only** here, and only slightly better than popularity-only on accuracy. The differences between CF-only and hybrid are within noise.
  The hybrid's real benefits are **coverage** (popularity-only recommends just 19% of the catalogue — everyone gets the same books), **cold-start handling** and **explanations**.
* A small weight search (on a different random split) showed accuracy is almost flat across weights (NDCG 0.129–0.131), so the default 45/40/15 was kept for explainability.
* The data is synthetic and small (99 books); rerun on Goodbooks-10k and report those numbers.
