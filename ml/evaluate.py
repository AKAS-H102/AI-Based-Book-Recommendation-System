"""
Offline evaluation of the recommender (hold-out method).

For every user: 80% of their ratings are used for training, 20% are hidden (test).
The model sees only the training part and recommends Top-K books.
A recommendation is a HIT if the user truly rated that hidden book >= 4 (i.e. "relevant").

Metrics:  Precision@K, Recall@K, NDCG@K, HitRate@K, Coverage
Compared: Random, Popularity-only, Content-only, Collaborative-only, Hybrid.

Run:  python -m ml.evaluate
"""
import argparse
import math
import numpy as np
import pandas as pd
from ml.engine import HybridRecommender


def split_ratings(ratings, test_frac=0.2, seed=42):
    rng = np.random.default_rng(seed)
    test_idx = []
    for _, g in ratings.groupby("user_id"):
        if len(g) < 5:
            continue
        n_test = max(1, int(round(len(g) * test_frac)))
        test_idx += list(rng.choice(g.index.to_numpy(), n_test, replace=False))
    test = ratings.loc[test_idx]
    return ratings.drop(test.index), test


def _metrics(recs, relevant, k):
    hits = [1 if b in relevant else 0 for b in recs]
    p = sum(hits) / k
    r = sum(hits) / len(relevant)
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return p, r, dcg / idcg, 1.0 if sum(hits) else 0.0


def evaluate(books, ratings, k=10, threshold=4, max_users=300, seed=42):
    train, test = split_ratings(ratings, seed=seed)
    rng = np.random.default_rng(seed)
    users = [u for u, g in test.groupby("user_id") if (g["rating"] >= threshold).any()]
    users = list(rng.choice(users, min(max_users, len(users)), replace=False))
    train_by_user = {u: dict(zip(g["book_id"], g["rating"])) for u, g in train.groupby("user_id")}
    test_by_user = {u: set(g.loc[g["rating"] >= threshold, "book_id"]) for u, g in test.groupby("user_id")}
    all_books = books["book_id"].tolist()

    configs = {
        "Random": None,
        "Popularity only": (0, 0, 1),
        "Content-based only": (1, 0, 0),
        "Collaborative only": (0, 1, 0),
        "Hybrid (proposed)": (0.45, 0.40, 0.15),
    }
    rows = []
    for name, w in configs.items():
        model = HybridRecommender().fit(books, train)
        P, R, N, H, seen = [], [], [], [], set()
        for u in users:
            seen_items = train_by_user.get(u, {})
            if name == "Random":
                cand = [b for b in all_books if b not in seen_items]
                recs = list(rng.choice(cand, k, replace=False))
            else:
                recs = [x["book_id"] for x in model.recommend(seen_items, k=k, weights=w, explain=False)]
            p, r, n, h = _metrics(recs, test_by_user[u], k)
            P.append(p); R.append(r); N.append(n); H.append(h); seen.update(recs)
        rows.append({"Model": name, f"Precision@{k}": np.mean(P), f"Recall@{k}": np.mean(R),
                     f"NDCG@{k}": np.mean(N), f"HitRate@{k}": np.mean(H), "Coverage": len(seen) / len(all_books)})
    df = pd.DataFrame(rows).set_index("Model").round(3)
    info = {"train_ratings": len(train), "test_ratings": len(test), "users_evaluated": len(users), "k": k}
    return df, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/processed")
    ap.add_argument("--k", type=int, default=10)
    a = ap.parse_args()
    books = pd.read_csv(f"{a.data}/books_clean.csv")
    ratings = pd.read_csv(f"{a.data}/ratings_clean.csv")
    df, info = evaluate(books, ratings, k=a.k)
    print(info)
    print(df.to_string())
    df.to_csv(f"{a.data}/evaluation_results.csv")
    print(f"\nSaved to {a.data}/evaluation_results.csv")


if __name__ == "__main__":
    main()
