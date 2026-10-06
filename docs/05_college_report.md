# AI-Based Book Recommendation System — Project Report
*(Replace the bracketed items with your details. Re-run `python -m ml.evaluate` on your final dataset and update the numbers in §14.)*

**Title:** AI-Based Book Recommendation System (BookWise)  **Submitted by:** [Name, Roll No.]  **Guide:** [Name]  **Department / College / Year:** [..]

## 1. Abstract
The number of books available online far exceeds what a reader can browse, and generic bestseller lists ignore personal taste.
This project presents *BookWise*, a web-based book recommendation system that learns each reader's preferences from ratings, favourites, viewing behaviour and chosen genres.
The system uses a **hybrid recommender** that combines content-based filtering (TF-IDF features of title, author, genre and description with cosine similarity),
item-based collaborative filtering (adjusted cosine similarity on mean-centred ratings) and a Bayesian popularity prior. The weights adapt to how much history a user has, which handles the
cold-start problem. Every recommendation is accompanied by a plain-language explanation. The application is built with Flask, SQLite and scikit-learn, and offers registration, search and filters, rating, favourites, history and profile pages.
The recommender is evaluated by hold-out testing with Precision@K, Recall@K, NDCG@K, HitRate@K and Coverage against random, popularity-only, content-only and collaborative-only baselines. A suite of 43 automated tests verifies the software.

**Keywords:** recommender system, hybrid filtering, TF-IDF, collaborative filtering, cold start, Flask.

## 2. Introduction
Recommender systems filter information overload by predicting which items a user will like. They power product, music, video and book suggestions.
Books are particularly suitable: rich text metadata (descriptions, genres, authors) allows content analysis, and reader communities produce large rating collections for collaborative methods.
This project designs, implements and evaluates such a system end-to-end: data pipeline, machine-learning model, database, web interface and tests.

## 3. Problem Statement
Readers waste time searching for books and generic lists do not reflect individual taste, do not learn from feedback, and do not explain themselves.
*Develop a web application that recommends books personally, improves with user interactions, handles new users, and justifies its suggestions.*

## 4. Existing System
* Bestseller / "top rated" lists and manual genre browsing — same output for everyone.
* Keyword search in library catalogues — requires the reader to already know what to look for.
* Large commercial platforms (e.g. Goodreads, Amazon) provide recommendations but are closed-source, give limited explanation and cannot be studied or modified.
**Limitations:** no personalisation, no explanation, no learning from feedback, poor handling of new users.

## 5. Proposed System
A hybrid recommender integrated into a web application. It (i) personalises using ratings, favourites, views and declared interests, (ii) adapts weights to the amount of user history (cold-start safe),
(iii) explains each recommendation, (iv) updates as soon as the user interacts, and (v) is open, simple and reproducible.

## 6. Objectives
1. Build a responsive web application for browsing, searching and filtering books.
2. Implement secure registration, login, logout and user profile.
3. Allow rating, favouriting and history tracking.
4. Develop and compare content-based, collaborative, popularity and hybrid recommenders.
5. Provide explanations for recommendations.
6. Evaluate with standard ranking metrics and verify with automated tests.

## 7. Scope
Included: single-language book catalogue, explicit (ratings, favourites) and implicit (views) feedback, offline training with lazy in-app retraining, evaluation, documentation.
Excluded: deep-learning models, social network features, admin panel, e-commerce, mobile app, multi-language text analysis.

## 8. Literature Survey
| Work | Contribution | Relevance |
|---|---|---|
| Resnick et al., *GroupLens* (CSCW 1994) | Introduced automated collaborative filtering for netnews | Foundation of the collaborative idea |
| Sarwar et al., *Item-based CF algorithms* (WWW 2001) | Item-item similarity is scalable and accurate | Basis of our CF component |
| Linden, Smith, York, *Amazon.com recommendations* (IEEE Internet Computing 2003) | Item-to-item CF deployed at industrial scale | Shows practicality of item-based CF |
| Salton & Buckley, *Term-weighting approaches* (1988) | TF-IDF weighting | Basis of our content features |
| Pazzani & Billsus, *Content-based recommendation systems* (2007) | Survey of content-based methods | Content component |
| Burke, *Hybrid recommender systems* (UMUAI 2002) | Taxonomy of hybridisation (weighted, switching, …) | Our design is a *weighted/adaptive* hybrid |
| Koren, Bell, Volinsky, *Matrix factorization techniques* (IEEE Computer 2009) | Latent-factor models | Considered; listed as future work |
| Ricci, Rokach, Shapira (eds.), *Recommender Systems Handbook* | Standard reference incl. evaluation | Metrics and cold-start discussion |
**Gap addressed:** most academic prototypes show one algorithm and no interface; this project integrates a hybrid, explainable recommender into a complete, tested application.

## 9. Methodology
Waterfall-style phases: requirement analysis → technology selection → design → data & ML → backend → frontend → integration → testing → documentation. Pipeline:
`raw data → cleaning → feature extraction (TF-IDF, rating matrix) → model fitting → evaluation → deployment into the web app → continuous use of user feedback`.

## 10. System Architecture
See `docs/01_analysis_and_design.md` §3.1–3.2 (architecture, data flow). Three layers: browser (HTML/CSS/JS) ↔ Flask (routes, API, services) ↔ SQLite + in-memory recommender.

## 11. Module Description
1. **Authentication** – registration with validation, salted password hashing, sessions, CSRF protection, login throttling.
2. **Book management** – list, search, filter (genre/author/rating), sort, paginate, detail page with rating distribution.
3. **Interaction** – rate (1–5), favourite, history log (view/rate/favourite events).
4. **Recommendation engine** – hybrid scoring, explanations, similar-books.
5. **Data pipeline** – cleaning, feature building, DB loading.
6. **Evaluation** – hold-out split, metrics, baselines.
7. **UI** – Home, Login/Register, Browse, Detail, For You, Favourites, History, Profile, How-it-works.

## 12. Dataset Description
Recommended: Goodbooks-10k (10,000 books, ≈6M ratings, ≈53k users; Zając). Attributes, cleaning steps and the sample dataset used for offline demo are in `docs/02_dataset_and_ml.md`.
*State clearly which dataset your reported results use. The bundled sample uses real book metadata but synthetic ratings.*

## 13. Algorithm / ML Model
Detailed in `docs/02_dataset_and_ml.md` §4.3–4.5: TF-IDF content profile, item-based CF with mean-centring and significance weighting, Bayesian popularity, adaptive weighted combination, explanation generation.

## 14. Results (replace with your final run)
Sample-data results (300 users, K=10): Random NDCG 0.059; Popularity 0.118; Content 0.101; Collaborative 0.131; **Hybrid 0.127**; coverage: popularity 19 % vs hybrid ≈100 %.
Observations: personalised models clearly beat random; hybrid matches the best single model on accuracy while giving far wider coverage, cold-start support and explanations.
Qualitative demonstration: a new user who selected *Fantasy/Science Fiction* received sci-fi picks with the reason "Matches your interest in Science Fiction"; after rating four biographies 5★ the top picks became biographies with reasons such as "Similar to *Becoming*, which you liked".

## 15. Implementation
Tools: Python 3.12, Flask 3, SQLite, pandas, NumPy, SciPy, scikit-learn. Folder structure, key files and run instructions are in `README.md`. Key implementation choices:
sparse matrices keep memory low; the model is cached and retrained lazily (≥ 30 s after new ratings); SQL is parameterised; all user input is validated.

## 16. Testing
43 automated tests (unit, functional, security, integration, recommendation-quality) — all pass. Full tables in `docs/04_testing.md`.

## 17. Advantages
Personalised and explainable · works for new users · learns from feedback · simple free stack · responsive UI · secure by design · reproducible and tested.

## 18. Limitations
* Bundled ratings are synthetic; real-world performance must be confirmed on a real dataset.
* Item similarity is recomputed for the active user's rated books on each request (fine for thousands of books; needs caching/ANN for millions).
* TF-IDF captures word overlap, not meaning (no semantic understanding); Goodbooks has no descriptions so tags stand in.
* Popularity bias and the "filter bubble" remain possible; no diversity re-ranking.
* Genres stored as a delimited string; single-process in-memory model; no email verification / password reset.
* Offline metrics do not measure real user satisfaction (needs an A/B test or user study).

## 19. Future Enhancements
Matrix factorisation (SVD/ALS) or neural embeddings (sentence-transformers) for descriptions · diversity/novelty re-ranking · real cover images and descriptions via an open books API ·
admin panel to add books · password reset & email verification · reading lists / "want to read" · user study and A/B test · caching and a proper job queue for retraining · Docker deployment · normalised genre tables.

## 20. Conclusion
BookWise demonstrates a complete, explainable, hybrid recommendation system integrated into a secure, responsive web application. The hybrid approach combines
the strengths of content-based, collaborative and popularity signals, handles cold start, and offers transparency. Evaluation shows clear gains over random recommendations and wide catalogue coverage.
The project meets all stated objectives and provides a base for further research.

## 21. References
1. P. Resnick, N. Iacovou, M. Suchak, P. Bergstrom, J. Riedl, "GroupLens: An open architecture for collaborative filtering of netnews," *Proc. ACM CSCW*, 1994.
2. B. Sarwar, G. Karypis, J. Konstan, J. Riedl, "Item-based collaborative filtering recommendation algorithms," *Proc. WWW*, 2001.
3. G. Linden, B. Smith, J. York, "Amazon.com recommendations: item-to-item collaborative filtering," *IEEE Internet Computing*, 7(1), 2003.
4. G. Salton, C. Buckley, "Term-weighting approaches in automatic text retrieval," *Information Processing & Management*, 24(5), 1988.
5. M. Pazzani, D. Billsus, "Content-based recommendation systems," in *The Adaptive Web*, Springer, 2007.
6. R. Burke, "Hybrid recommender systems: survey and experiments," *User Modeling and User-Adapted Interaction*, 12(4), 2002.
7. Y. Koren, R. Bell, C. Volinsky, "Matrix factorization techniques for recommender systems," *IEEE Computer*, 42(8), 2009.
8. F. Ricci, L. Rokach, B. Shapira (eds.), *Recommender Systems Handbook*, Springer.
9. F. Pedregosa et al., "Scikit-learn: machine learning in Python," *JMLR*, 12, 2011.
10. Z. Zając, *goodbooks-10k* dataset, https://github.com/zygmuntz/goodbooks-10k (accessed [date]).
11. Flask documentation, https://flask.palletsprojects.com ; SQLite documentation, https://sqlite.org.
> Verify each reference's details (volume/pages/URL) against the originals before submission.
