from unittest.mock import Mock

import pandas as pd
import pytest
import st_keyup
import streamlit as st
from streamlit.testing.v1 import AppTest

import app_service


@pytest.fixture
def ui(monkeypatch):
    st.cache_data.clear()
    st.cache_resource.clear()
    catalog = pd.DataFrame(
        [
            {
                "parent_asin": f"book-{i}",
                "title": f"Title {i}",
                "author": "Test Author",
                "genre": "Fiction",
            }
            for i in range(30)
        ]
    )
    backend = Mock(
        side_effect=lambda selected, model, k: [
            {**book, "score": 1.0}
            for book in catalog.to_dict("records")
            if book["parent_asin"] not in selected
        ][:k]
    )
    monkeypatch.setattr(app_service, "load_catalog", lambda: catalog)
    monkeypatch.setattr(app_service, "get_backend", lambda: backend)

    def search(text, limit=20):
        text = text.strip().lower()
        hits = catalog["title"].str.lower().str.contains(text, regex=False) | catalog[
            "author"
        ].str.lower().str.contains(text, regex=False)
        return catalog[hits].head(limit).to_dict("records")

    monkeypatch.setattr(app_service, "get_search", lambda: search)
    # AppTest cannot type in a third-party iframe. Replace only that boundary.
    monkeypatch.setattr(
        st_keyup,
        "st_keyup",
        lambda label, **kwargs: st.text_input(label, key=kwargs["key"]),
    )
    app = AppTest.from_file(str(app_service.ROOT / "app.py")).run()
    yield app, backend
    st.cache_data.clear()
    st.cache_resource.clear()


def book_checkbox(app, index):
    return next(item for item in app.checkbox if item.key == f"book_book-{index}")


def button(app, label):
    return next(item for item in app.button if item.label.startswith(label))


def selection_buttons(app):
    return [item.key.removeprefix("remove_") for item in app.button
            if item.key and item.key.startswith("remove_")]


def confirm(app):
    button(app, "Confirm selection").click().run()


def recommend(app):
    button(app, "Get recommendations").click().run()


def test_catalog_visible_immediately_and_nothing_computed(ui):
    app, backend = ui
    assert not app.exception
    assert len(app.checkbox) == 12
    assert book_checkbox(app, 0).label == "Title 0 — Test Author"
    assert book_checkbox(app, 11).value is False
    assert [item.value for item in app.info] == ["Select at least one book"]
    assert button(app, "Confirm selection").disabled
    assert not app.radio
    assert not app.multiselect
    backend.assert_not_called()


def test_selection_list_shows_all_books_and_nothing_runs_before_click(ui):
    app, backend = ui
    for index in range(3):
        book_checkbox(app, index).check().run()
    assert not app.exception
    assert selection_buttons(app) == ["book-0", "book-1", "book-2"]
    assert not app.dataframe
    backend.assert_not_called()
    app.text_input[0].set_value("Title 29").run()
    assert len(app.checkbox) == 1
    assert selection_buttons(app) == ["book-0", "book-1", "book-2"]
    app.text_input[0].set_value("").run()
    assert all(book_checkbox(app, index).value for index in range(3))
    button(app, "✕").click().run()  # removes the first one
    assert selection_buttons(app) == ["book-1", "book-2"]
    assert not book_checkbox(app, 0).value
    button(app, "Clear all").click().run()
    assert selection_buttons(app) == []
    assert not book_checkbox(app, 1).value
    backend.assert_not_called()


def test_confirm_then_recommend(ui):
    app, backend = ui
    book_checkbox(app, 0).check().run()
    book_checkbox(app, 2).check().run()
    confirm(app)
    assert not app.checkbox
    assert app.radio
    assert not app.dataframe
    backend.assert_not_called()
    recommend(app)
    assert len(app.dataframe[0].value) == 10
    backend.assert_called_once_with(["book-0", "book-2"], "popularity", k=10)
    app.run()
    assert backend.call_count == 1
    assert app.dataframe
    app.radio[0].set_value("itemknn").run()
    assert not app.dataframe
    assert "Settings changed" in app.info[0].value
    assert backend.call_count == 1
    recommend(app)
    backend.assert_called_with(["book-0", "book-2"], "itemknn", k=10)
    button(app, "← Edit selection").click().run()
    assert book_checkbox(app, 0).value and book_checkbox(app, 2).value
    assert not app.dataframe
    assert not app.exception


def test_pagination_and_search_beyond_twenty_results(ui):
    app, backend = ui
    app.text_input[0].set_value("test author").run()
    for _ in range(2):
        button(app, "Next →").click().run()
    book_checkbox(app, 29).check().run()
    app.text_input[0].set_value("Title 0").run()
    assert book_checkbox(app, 0)
    assert selection_buttons(app) == ["book-29"]
    assert app.session_state["catalog_page"] == 0
    backend.assert_not_called()


def test_limit_and_removal_preserve_checkbox_state(ui):
    app, backend = ui
    for index in range(10):
        book_checkbox(app, index).check().run()
    assert len(selection_buttons(app)) == 10
    assert book_checkbox(app, 10).disabled
    assert not book_checkbox(app, 0).disabled
    book_checkbox(app, 0).uncheck().run()
    assert not book_checkbox(app, 10).disabled
    assert len(selection_buttons(app)) == 9
    assert not app.exception


def test_model_comparison_and_isolated_error(ui):
    app, backend = ui
    book_checkbox(app, 0).check().run()
    confirm(app)
    success = backend.side_effect

    def mixed(selected, model, k):
        if model == "als":
            return [{"invalid": True}]
        return success(selected, model, k)

    backend.side_effect = mixed
    app.toggle[0].set_value(True).run()
    assert app.radio[0].disabled
    backend.assert_not_called()
    recommend(app)
    assert [call.args[1] for call in backend.call_args_list] == list(app_service.MODELS)
    assert len(app.dataframe) == 2
    assert len(app.error) == 1
    assert not app.exception


def test_fallback_and_session_isolation(ui):
    first, backend = ui
    book_checkbox(first, 0).check().run()
    confirm(first)
    output = backend.side_effect(["book-0"], "popularity", 10)
    backend.side_effect = [[], output]
    first.radio[0].set_value("itemknn").run()
    recommend(first)
    assert "fallback popularity" in first.warning[0].value
    second = AppTest.from_file(str(app_service.ROOT / "app.py")).run()
    assert first.session_state["selected"] == ["book-0"]
    assert second.session_state["selected"] == []
    assert not second.dataframe
    assert not first.exception
    assert not second.exception
