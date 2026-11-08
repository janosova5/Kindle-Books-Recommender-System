"""Validation and orchestration only; recommendation models live in recommender.py."""

from dataclasses import dataclass
from importlib import import_module
import logging
from pathlib import Path
from typing import Callable

import pandas as pd


ROOT = Path(__file__).resolve().parent
MODELS = {
    "popularity": ("Popularity", "The most popular books, without personalisation."),
    "itemknn": ("ItemKNN", "Books similar to the ones you selected."),
    "als": ("ALS", "Personalised recommendations based on latent factors."),
}
Recommend = Callable[..., list[dict]]
LOGGER = logging.getLogger(__name__)


class InputError(ValueError):
    """An input problem that can be displayed to the user."""


class RecommendationError(RuntimeError):
    """A backend or output-contract problem."""


@dataclass
class RecommendationResult:
    books: list[dict]
    warning: str | None = None


def validate_selection(liked_asins: list[str], model: str) -> list[str]:
    if model not in MODELS:
        raise InputError("Select a valid model")
    if not isinstance(liked_asins, list) or any(
        not isinstance(asin, str) or not asin.strip() for asin in liked_asins
    ):
        raise InputError("Select valid books from the catalog")
    unique = list(dict.fromkeys(liked_asins))
    if not unique:
        raise InputError("Select at least one book")
    if len(unique) > 10:
        raise InputError("Select no more than 10 books")
    return unique


def load_catalog(path: Path = ROOT / "artifacts" / "catalog.parquet") -> pd.DataFrame:
    catalog = pd.read_parquet(path)
    # The supplied catalog may call its identifier ID rather than parent_asin.
    if "parent_asin" not in catalog.columns and "ID" in catalog.columns:
        catalog = catalog.rename(columns={"ID": "parent_asin"})
    required = {"parent_asin", "title", "author", "genre"}
    if not required.issubset(catalog.columns):
        raise ValueError("Catalog must contain parent_asin (or ID), title, author, genre")
    catalog = catalog[list(sorted(required))].copy()
    if catalog["parent_asin"].isna().any():
        raise ValueError("Catalog contains missing book IDs")
    catalog["parent_asin"] = catalog["parent_asin"].astype(str)
    if catalog["parent_asin"].str.strip().eq("").any():
        raise ValueError("Catalog contains empty book IDs")
    if catalog["parent_asin"].duplicated().any():
        raise ValueError("Catalog contains duplicate book IDs")
    for column in ("title", "author", "genre"):
        catalog[column] = catalog[column].fillna("").astype(str)
    return catalog.reset_index(drop=True)


def search_books(
    catalog: pd.DataFrame, query: str, limit: int | None = 20
) -> pd.DataFrame:
    query = query.strip()
    if not query:
        return catalog.iloc[:0]
    matches = catalog["title"].str.contains(query, case=False, regex=False) | catalog[
        "author"
    ].str.contains(query, case=False, regex=False)
    filtered = catalog.loc[matches]
    return filtered if limit is None else filtered.head(limit)


def get_backend() -> Recommend:
    return import_module("recommender").recommend


def backend_is_demo() -> bool:
    return getattr(import_module("recommender"), "IS_DEMO", False) is True


def _check_books(books: list[dict], selected: list[str]) -> list[dict]:
    if not isinstance(books, list):
        raise RecommendationError("recommend() must return a list")
    if len(books) > 10:
        raise RecommendationError("recommend() returned more than 10 books")
    seen = set(selected)
    for book in books:
        if not isinstance(book, dict) or not {
            "parent_asin", "title", "author", "genre", "score"
        }.issubset(book):
            raise RecommendationError("recommend() returned an invalid book")
        asin = book["parent_asin"]
        if not isinstance(asin, str) or not asin.strip():
            raise RecommendationError("recommend() returned an invalid book ID")
        if asin in seen:
            raise RecommendationError("recommend() returned a selected or duplicate book")
        seen.add(asin)
    return books


def recommend_books(
    liked_asins: list[str], model: str, backend: Recommend | None = None
) -> RecommendationResult:
    selected = validate_selection(liked_asins, model)
    backend = backend if backend is not None else get_backend()
    warning = None
    try:
        books = backend(selected.copy(), model, k=10)
    except Exception as exc:
        LOGGER.exception("Recommendation backend failed for model %s", model)
        if model == "popularity":
            raise RecommendationError("Popularity recommendations are unavailable") from exc
        books = []
        warning = "Selected model failed. Showing fallback popularity recommendations."
    # Invalid output is a contract error, not a reason to hide a model bug.
    books = _check_books(books, selected)
    if not books and model != "popularity":
        warning = warning or (
            "Selected model could not recommend books. "
            "Showing fallback popularity recommendations."
        )
        try:
            books = _check_books(backend(selected.copy(), "popularity", k=10), selected)
        except Exception as exc:
            LOGGER.exception("Popularity fallback failed")
            raise RecommendationError("Fallback recommendations are unavailable") from exc
    if not books:
        raise RecommendationError("No recommendations are available for this selection")
    if len(books) < 10:
        warning = (warning + " " if warning else "") + (
            f"Only {len(books)} recommendations are available instead of 10."
        )
    return RecommendationResult(books, warning)
