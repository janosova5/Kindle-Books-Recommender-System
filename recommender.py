"""Kindle book recommender: loads the trained artifacts and returns top-k books."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

ART = Path(__file__).resolve().parent / "artifacts"
MODELS = ("popularity", "itemknn", "als")
MAX_LIKED = 10


@lru_cache(maxsize=1)
def _load():
    cat = pd.read_parquet(ART / "catalog.parquet")
    cat = cat.fillna({"title": "Unknown title", "author": "Unknown author", "genre": "Unknown genre"})
    params = json.loads((ART / "model_params.json").read_text())
    pop = json.loads((ART / "popularity.json").read_text())
    sim = sp.load_npz(ART / "itemknn_sim.npz").tocsr()
    Y = np.load(ART / "als_item_factors.npy").astype(np.float64)
    index = {a: i for i, a in enumerate(cat["parent_asin"])}
    return cat, params, pop, sim, Y, index


def search(text, limit=20):
    """Books whose title or author contains the text (case-insensitive)."""
    cat = _load()[0]
    t = str(text).strip().lower()
    if not t:
        return []
    hit = cat["title"].fillna("").str.lower().str.contains(t, regex=False) | \
          cat["author"].fillna("").str.lower().str.contains(t, regex=False)
    return cat[hit].head(limit).to_dict("records")


def recommend(liked_asins, model="als", k=10):
    """Return k recommended books (list of dicts) for the books the user liked.

    Raises ValueError for an unknown model, an empty or too long selection, or books not in the catalogue.
    If a model cannot score any book, the most popular books are returned with fallback=True.
    """
    if model not in MODELS:
        raise ValueError(f"Unknown model '{model}'. Choose one of {MODELS}.")
    if not isinstance(k, int) or not 1 <= k <= 50:
        raise ValueError("k must be an integer between 1 and 50.")
    cat, params, pop, sim, Y, index = _load()
    liked = list(dict.fromkeys(liked_asins or []))          # remove duplicates, keep order
    if not liked:
        raise ValueError("Select at least one book.")
    if len(liked) > MAX_LIKED:
        raise ValueError(f"Select at most {MAX_LIKED} books.")
    unknown = [a for a in liked if a not in index]
    if unknown:
        raise ValueError(f"Books not in the catalogue: {unknown}")
    li = np.array([index[a] for a in liked])

    scores = None
    if model == "itemknn":
        s = np.asarray(sim[li].sum(axis=0)).ravel().astype(np.float64)
        scores = s if (s > 0).any() else None
    elif model == "als":
        lam, alpha = params["als"]["regularization"], params["als"]["alpha"]
        A = Y.T @ Y + lam * np.eye(Y.shape[1]) + (alpha - 1) * Y[li].T @ Y[li]
        u = np.linalg.solve(A, alpha * Y[li].sum(axis=0))
        scores = Y @ u

    fallback = scores is None and model != "popularity"
    if scores is None:
        order = [index[a] for a in pop]
        score_of = {i: float(len(pop) - r) for r, i in enumerate(order)}
    else:
        scores[li] = -np.inf
        order = np.argsort(-scores, kind="stable")
        score_of = None
    liked_set = set(li.tolist())
    out = []
    for i in order:
        i = int(i)
        if i in liked_set:
            continue
        row = cat.iloc[i]
        out.append({"rank": len(out) + 1, "parent_asin": row["parent_asin"], "title": row["title"],
                    "author": row["author"], "genre": row["genre"],
                    "score": score_of[i] if score_of else float(scores[i]), "fallback": fallback})
        if len(out) == k:
            break
    return out
