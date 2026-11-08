"""Integration gate: golden outputs must match the installed backend."""

import json
import math

import pytest

from app_service import ROOT, load_catalog, recommend_books

# Only the app's output contract is compared; extra backend fields
# (e.g. rank, fallback) are ignored.
FIELDS = ("parent_asin", "title", "author", "genre", "score")


def _normalize(books):
    # JSON stores missing values as null, the backend may return NaN.
    return [
        {
            key: None
            if isinstance(book.get(key), float) and math.isnan(book[key])
            else book.get(key)
            for key in FIELDS
        }
        for book in books
    ]


def test_backend_matches_three_reference_inputs():
    required = [
        ROOT / "expected_outputs.json",
        ROOT / "recommender.py",
        ROOT / "artifacts" / "catalog.parquet",
    ]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        pytest.skip("Awaiting supplied integration files: " + ", ".join(missing))
    with required[0].open(encoding="utf-8") as handle:
        data = json.load(handle)
    cases = data["cases"] if isinstance(data, dict) else data
    assert isinstance(cases, list) and len(cases) >= 3
    catalog_ids = set(load_catalog()["parent_asin"])
    for case in cases:
        selected = case["liked_asins"]
        assert set(selected) <= catalog_ids
        first = recommend_books(selected, case["model"])
        second = recommend_books(selected, case["model"])
        assert _normalize(first.books) == _normalize(case["expected"])
        assert first == second
        assert len(first.books) == 10
        output_ids = {book["parent_asin"] for book in first.books}
        assert output_ids <= catalog_ids
        assert not set(selected) & output_ids
