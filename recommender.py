"""Kindle book recommender: loads the trained artifacts and returns top-k books."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
MODELS = ("popularity", "itemknn", "als")
MAX_LIKED = 10


@lru_cache(maxsize=1)
def _load():
    """Load the catalogue and the trained models once (later calls reuse them)."""
    catalog = pd.read_parquet(ARTIFACTS / "catalog.parquet")
    catalog = catalog.fillna({"title": "Unknown title", "author": "Unknown author", "genre": "Unknown genre"})
    params = json.loads((ARTIFACTS / "model_params.json").read_text())
    popular_books = json.loads((ARTIFACTS / "popularity.json").read_text())        # book IDs, most popular first
    similarity = sp.load_npz(ARTIFACTS / "itemknn_sim.npz").tocsr()               # ItemKNN: book x book
    book_vectors = np.load(ARTIFACTS / "als_item_factors.npy").astype(np.float64)  # ALS: book x factors
    position_of = {book_id: pos for pos, book_id in enumerate(catalog["parent_asin"])}
    return catalog, params, popular_books, similarity, book_vectors, position_of


def search(text, limit=20):
    """Books whose title or author contains the text (case-insensitive)."""
    catalog = _load()[0]
    query = str(text).strip().lower()
    if not query:
        return []
    matches = (catalog["title"].str.lower().str.contains(query, regex=False)
               | catalog["author"].str.lower().str.contains(query, regex=False))
    return catalog[matches].head(limit).to_dict("records")


def recommend(liked_asins, model="als", k=10):
    """Return k recommended books (list of dicts) for the books the user liked.

    Raises ValueError for an unknown model, an empty or too long selection, or books not in the catalogue.
    If a model cannot score any book, the most popular books are returned with fallback=True.
    """
    # 1. check the inputs
    if model not in MODELS:
        raise ValueError(f"Unknown model '{model}'. Choose one of {MODELS}.")
    if not isinstance(k, int) or not 1 <= k <= 50:
        raise ValueError("k must be an integer between 1 and 50.")
    catalog, params, popular_books, similarity, book_vectors, position_of = _load()
    liked = list(dict.fromkeys(liked_asins or []))                  # remove duplicates, keep order
    if not liked:
        raise ValueError("Select at least one book.")
    if len(liked) > MAX_LIKED:
        raise ValueError(f"Select at most {MAX_LIKED} books.")
    unknown = [book_id for book_id in liked if book_id not in position_of]
    if unknown:
        raise ValueError(f"Books not in the catalogue: {unknown}")
    liked_pos = np.array([position_of[book_id] for book_id in liked])

    # 2. score all catalogue books with the chosen model
    scores = None
    if model == "itemknn":
        # sum of similarities to the liked books
        knn_scores = np.asarray(similarity[liked_pos].sum(axis=0)).ravel().astype(np.float64)
        scores = knn_scores if (knn_scores > 0).any() else None
    elif model == "als":
        # vector of the new user: the same ridge regression step that ALS solves for every user
        regularization, alpha = params["als"]["regularization"], params["als"]["alpha"]
        liked_vectors = book_vectors[liked_pos]
        system_matrix = (book_vectors.T @ book_vectors + regularization * np.eye(book_vectors.shape[1])
                         + (alpha - 1) * liked_vectors.T @ liked_vectors)
        user_vector = np.linalg.solve(system_matrix, alpha * liked_vectors.sum(axis=0))
        scores = book_vectors @ user_vector

    # 3. order the books: by score, or by popularity if there is no score
    fallback = scores is None and model != "popularity"
    if scores is None:
        order = [position_of[book_id] for book_id in popular_books]
        popularity_score = {pos: float(len(popular_books) - rank) for rank, pos in enumerate(order)}
    else:
        scores[liked_pos] = -np.inf                                  # never recommend the liked books
        order = np.argsort(-scores, kind="stable")                   # stable = same order for equal scores
        popularity_score = None

    # 4. build the list of the top k books
    liked_set = set(liked_pos.tolist())
    recommendations = []
    for pos in order:
        pos = int(pos)
        if pos in liked_set:
            continue
        book = catalog.iloc[pos]
        recommendations.append({
            "rank": len(recommendations) + 1, "parent_asin": book["parent_asin"], "title": book["title"],
            "author": book["author"], "genre": book["genre"],
            "score": popularity_score[pos] if popularity_score else float(scores[pos]), "fallback": fallback})
        if len(recommendations) == k:
            break
    return recommendations
