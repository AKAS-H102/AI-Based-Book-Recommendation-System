"""
Hybrid book recommendation engine (the "AI" part of the project).

Three signals are combined into one score for every book the user has not read yet:

 1. CONTENT      TF-IDF over title/author/genres/description -> cosine similarity between a book
                 and the user's taste profile (liked books + chosen genres).
 2. COLLABORATIVE Item-based CF on mean-centred ratings: "people who liked book A also liked B".
 3. POPULARITY   Bayesian-weighted average rating (helps cold-start users with no history).

final_score = w_content * content + w_cf * cf + w_pop * popularity
The weights adapt to how much history the user has (few ratings -> trust CF less, popularity more).
Every recommendation carries human-readable reasons (explainability).
"""
import re
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


def _tok(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def _split_genres(g):
    return [x for x in str(g).split(";") if x]


class HybridRecommender:
    def __init__(self, w_content=0.45, w_cf=0.40, w_pop=0.15, genre_weight=2.0, cf_shrink=20):
        self.w = (w_content, w_cf, w_pop)
        self.genre_weight = genre_weight
        self.cf_shrink = cf_shrink      # co-rater count at which similarity is fully trusted
        self.fitted = False

    # ------------------------------------------------------------------ training
    def fit(self, books: pd.DataFrame, ratings: pd.DataFrame):
        """books: book_id,title,author,genres,description  | ratings: user_id,book_id,rating"""
        self.books = books.reset_index(drop=True)
        self.ids = self.books["book_id"].to_numpy()
        self.idx = {int(b): i for i, b in enumerate(self.ids)}
        self.titles = self.books["title"].tolist()
        self.genre_sets = [set(_split_genres(g)) for g in self.books["genres"]]
        n = len(self.books)

        # --- content features (TF-IDF) ---
        text = (self.books["description"].fillna("") + " "
                + self.books["genres"].apply(lambda g: " ".join(_tok(x) for x in _split_genres(g)) + " ").map(lambda s: s * 3)
                + self.books["author"].fillna("").apply(lambda a: (_tok(a) + " ") * 2)
                + self.books["title"].fillna(""))
        self.tfidf = TfidfVectorizer(stop_words="english", sublinear_tf=True, ngram_range=(1, 2), max_features=30000)
        self.X = self.tfidf.fit_transform(text)            # rows are L2-normalised

        # --- collaborative features (item-item) ---
        r = ratings[ratings["book_id"].isin(self.idx)].copy()
        r["i"] = r["book_id"].map(self.idx)
        r["u"] = pd.factorize(r["user_id"])[0]
        n_users = r["u"].max() + 1 if len(r) else 0
        self.n_ratings = len(r)
        if len(r):
            user_mean = r.groupby("u")["rating"].transform("mean")
            centred = (r["rating"] - user_mean).to_numpy()
            R = sparse.csr_matrix((centred, (r["i"], r["u"])), shape=(n, n_users))
            self.Rn = normalize(R)                                              # items x users
            self.B = sparse.csr_matrix((np.ones(len(r)), (r["i"], r["u"])), shape=(n, n_users))
            stats = r.groupby("i")["rating"].agg(["mean", "count"])
            v = np.zeros(n); m_ = np.zeros(n)
            v[stats.index] = stats["count"]; m_[stats.index] = stats["mean"]
            C = r["rating"].mean(); m = max(1.0, np.median(stats["count"]))
            wr = np.where(v > 0, (v / (v + m)) * m_ + (m / (v + m)) * C, C)
            self.pop = (wr - wr.min()) / (wr.max() - wr.min() + 1e-9)
            self.avg = np.where(v > 0, m_, 0.0); self.cnt = v
        else:
            self.Rn = self.B = None
            self.pop = np.zeros(n); self.avg = np.zeros(n); self.cnt = np.zeros(n)
        self.fitted = True
        return self

    # --------------------------------------------------------------- recommending
    @staticmethod
    def _scale(v):
        v = np.clip(v, 0, None)
        mx = v.max()
        return v / mx if mx > 0 else v

    def recommend(self, interactions, genres=None, k=10, exclude=None, weights=None, explain=True, implicit=None):
        """
        interactions : {book_id: rating 1-5}  (the app passes favourites as 5 if not rated)
        genres       : list of genre names the user said they like (helps cold start)
        implicit     : list of book_ids the user only viewed (weak positive signal, content only)
        returns      : list of dicts {book_id, score, match_pct, components, reasons}
        """
        n = len(self.ids)
        rated = [(self.idx[int(b)], float(r)) for b, r in interactions.items() if int(b) in self.idx]
        rows = [i for i, _ in rated]
        n_int = len(rated)

        # ---- content score ----
        profile = None
        if rated:
            w = np.array([r - 3.0 for _, r in rated])            # 5->+2 ... 1->-2
            profile = sparse.csr_matrix(w) @ self.X[rows]
        imp = [self.idx[int(b)] for b in (implicit or []) if int(b) in self.idx and self.idx[int(b)] not in set(rows)]
        if imp:
            iv = sparse.csr_matrix(np.full(len(imp), 0.5)) @ self.X[imp]
            profile = iv if profile is None else profile + iv
        if genres:
            gv = self.tfidf.transform([" ".join(_tok(g) + " " + _tok(g) for g in genres)])
            gv = normalize(gv) * self.genre_weight
            profile = gv if profile is None else profile + gv
        content = np.zeros(n)
        if profile is not None and profile.nnz:
            content = np.asarray((self.X @ profile.T).todense()).ravel()

        # ---- collaborative score ----
        cf = np.zeros(n)
        S = None
        if rated and self.Rn is not None:
            wv = np.array([r - 3.0 for _, r in rated])             # 3 stars = neutral; 5 -> +2, 1 -> -2
            S = (self.Rn[rows] @ self.Rn.T).toarray()
            co = (self.B[rows] @ self.B.T).toarray()
            S = S * np.minimum(co, self.cf_shrink) / self.cf_shrink       # significance weighting
            S[np.arange(len(rows)), rows] = 0.0
            cf = (wv @ S) / (np.abs(S).sum(axis=0) + 1.0)

        content, cf = self._scale(content), self._scale(cf)
        pop = self.pop

        # ---- adaptive weights ----
        wc, wf, wp = weights or self.w
        conf = min(1.0, n_int / 8.0)
        wc = wc if profile is not None else 0.0
        wf = wf * conf
        wp = wp * (1.0 + 2.0 * (1.0 - conf))
        tot = wc + wf + wp
        wc, wf, wp = (wc / tot, wf / tot, wp / tot) if tot > 0 else (0, 0, 1.0)
        score = wc * content + wf * cf + wp * pop

        blocked = set(rows) | {self.idx[int(b)] for b in (exclude or []) if int(b) in self.idx}
        if blocked:
            score[list(blocked)] = -np.inf
        k = min(k, n - len(blocked))
        if k <= 0:
            return []
        top = np.argpartition(-score, k - 1)[:k]
        top = top[np.argsort(-score[top])]

        out = []
        for j in top:
            item = {"book_id": int(self.ids[j]), "score": float(score[j]),
                    "match_pct": int(round(100 * max(0.0, min(1.0, score[j])))),
                    "components": {"content": round(float(wc * content[j]), 3),
                                   "collaborative": round(float(wf * cf[j]), 3),
                                   "popularity": round(float(wp * pop[j]), 3)}}
            if explain:
                item["reasons"] = self._reasons(j, rated, rows, S, genres, wc * content[j], wf * cf[j], wp * pop[j])
            out.append(item)
        return out

    # --------------------------------------------------------------- explanations
    def _reasons(self, j, rated, rows, S, genres, c_part, f_part, p_part):
        parts = sorted([("content", c_part), ("cf", f_part), ("pop", p_part)], key=lambda x: -x[1])
        reasons = []
        for name, val in parts:
            if val <= 0 or len(reasons) >= 2:
                continue
            if name == "content":
                liked = [(i, r) for i, r in rated if r >= 4]
                best, bs = None, 0.12
                if liked:
                    sims = (self.X[[i for i, _ in liked]] @ self.X[j].T).toarray().ravel()
                    t = int(np.argmax(sims))
                    if sims[t] > bs:
                        best = liked[t][0]
                if best is not None:
                    shared = sorted(self.genre_sets[best] & self.genre_sets[j])
                    extra = f" (shared genres: {', '.join(shared)})" if shared else ""
                    reasons.append(f"Similar to \"{self.titles[best]}\", which you liked{extra}")
                elif genres and (set(genres) & self.genre_sets[j]):
                    reasons.append("Matches your interest in " + ", ".join(sorted(set(genres) & self.genre_sets[j])))
            elif name == "cf" and S is not None:
                contrib = np.array([(r - 3.0) for _, r in rated]) * S[:, j]
                t = int(np.argmax(contrib))
                if contrib[t] > 0:
                    reasons.append(f"Readers who liked \"{self.titles[rows[t]]}\" also liked this book")
            elif name == "pop" and self.cnt[j] > 0:
                reasons.append(f"Highly rated by the community ({self.avg[j]:.1f}★ from {int(self.cnt[j])} ratings)")
        if not reasons:
            reasons.append("Popular pick to get you started — rate a few books to personalise this")
        return reasons

    # --------------------------------------------------------------- similar books
    def similar(self, book_id, k=6):
        """Books most similar to a given book (content similarity + item-item CF)."""
        j = self.idx.get(int(book_id))
        if j is None:
            return []
        sc = np.asarray((self.X @ self.X[j].T).todense()).ravel()
        if self.Rn is not None:
            cfs = (self.Rn[j] @ self.Rn.T).toarray().ravel()
            sc = 0.7 * sc + 0.3 * np.clip(cfs, 0, None)
        sc[j] = -np.inf
        top = np.argsort(-sc)[:k]
        out = []
        for t in top:
            shared = sorted(self.genre_sets[j] & self.genre_sets[t])
            out.append({"book_id": int(self.ids[t]), "score": float(sc[t]),
                        "reasons": [("Shares genres: " + ", ".join(shared)) if shared else "Similar description and style"]})
        return out
