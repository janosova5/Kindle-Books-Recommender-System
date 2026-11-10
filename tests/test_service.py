from unittest.mock import Mock

import pandas as pd
import pytest

from app_service import (
    InputError,
    RecommendationError,
    load_catalog,
    recommend_books,
    search_books,
)


def books(count=10):
    return [
        {
            "parent_asin": f"result-{index}",
            "title": f"Book {index}",
            "author": "Synthetic Author",
            "genre": "Fiction",
            "score": 1.0 / (index + 1),
        }
        for index in range(count)
    ]


@pytest.mark.parametrize(
    "selection, model, message",
    [
        ([], "als", "Select at least one book"),
        ([str(i) for i in range(11)], "als", "Select no more than 10 books"),
        (["input"], "unknown", "Select a valid model"),
        ([""], "als", "Select valid books"),
    ],
)
def test_invalid_input_never_calls_backend(selection, model, message):
    backend = Mock()
    with pytest.raises(InputError, match=message):
        recommend_books(selection, model, backend)
    backend.assert_not_called()


def test_duplicates_are_ignored_and_order_preserved():
    backend = Mock(return_value=books())
    result = recommend_books(["first", "second", "first"], "als", backend)
    backend.assert_called_once_with(["first", "second"], "als", k=10)
    assert result.books == books()
    assert result.warning is None


@pytest.mark.parametrize("failure", [[], RuntimeError("No neighbors")])
def test_unavailable_model_uses_popularity_with_warning(failure):
    backend = Mock(side_effect=[failure, books()])
    result = recommend_books(["input"], "itemknn", backend)
    assert result.books == books()
    assert "fallback popularity" in result.warning
    assert backend.call_args_list[1].args == (["input"], "popularity")


def test_failed_fallback_is_explicit_error():
    backend = Mock(side_effect=[[], RuntimeError("Unavailable")])
    with pytest.raises(RecommendationError, match="Fallback"):
        recommend_books(["input"], "als", backend)


@pytest.mark.parametrize("failure", [[], RuntimeError("Unavailable")])
def test_unavailable_popularity_is_explicit_error_without_retry(failure):
    backend = Mock(side_effect=[failure])
    with pytest.raises(RecommendationError):
        recommend_books(["input"], "popularity", backend)
    assert backend.call_count == 1


def test_invalid_output_is_not_hidden_by_fallback():
    backend = Mock(return_value=[{"parent_asin": "incomplete"}])
    with pytest.raises(RecommendationError, match="invalid book"):
        recommend_books(["input"], "als", backend)
    assert backend.call_count == 1


def test_selected_book_is_rejected_not_silently_removed():
    with pytest.raises(RecommendationError, match="selected or duplicate"):
        recommend_books(["result-0"], "als", Mock(return_value=books()))


def test_duplicate_recommendations_are_rejected():
    output = books()
    output[1] = output[0]
    with pytest.raises(RecommendationError, match="selected or duplicate"):
        recommend_books(["input"], "als", Mock(return_value=output))


def test_identical_input_has_identical_output_without_reordering():
    backend = Mock(return_value=books())
    first = recommend_books(["input"], "als", backend)
    second = recommend_books(["input"], "als", backend)
    assert first == second
    assert not {"input"} & {book["parent_asin"] for book in first.books}


def test_short_output_is_reported():
    result = recommend_books(["input"], "als", Mock(return_value=books(2)))
    assert "Only 2" in result.warning


def test_search_delegates_to_recommender_search():
    search = Mock(return_value=[
        {"parent_asin": "a", "title": "A [Book]", "author": "Alice", "genre": "",
         "extra": 1},
    ])
    found = search_books(" book ", limit=None, search=search)
    search.assert_called_once_with("book", limit=None)
    assert found.to_dict("records") == [
        {"parent_asin": "a", "title": "A [Book]", "author": "Alice", "genre": ""}
    ]
    assert search_books(" ", search=search).empty
    assert search.call_count == 1


def test_search_uses_real_recommender_search():
    found = search_books("hoover", limit=5)
    assert 0 < len(found) <= 5
    assert found["author"].str.lower().str.contains("hoover").any()


def test_catalog_supports_id_column_and_missing_metadata(tmp_path):
    path = tmp_path / "catalog.parquet"
    pd.DataFrame(
        [{"ID": "a", "title": "Title", "author": None, "genre": None}]
    ).to_parquet(path)
    catalog = load_catalog(path)
    assert catalog.iloc[0]["parent_asin"] == "a"
    assert catalog.iloc[0]["author"] == ""


def test_backend_flagged_fallback_shows_warning():
    flagged = [{**book, "fallback": True} for book in books()]
    result = recommend_books(["input"], "itemknn", Mock(return_value=flagged))
    assert result.books == flagged
    assert "fallback popularity" in result.warning
    popular = recommend_books(["input"], "popularity", Mock(return_value=flagged))
    assert popular.warning is None
