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


def test_catalog_visible_immediately_and_empty_selection_is_compact(ui):
    app, backend = ui
    assert not app.exception
    assert len(app.checkbox) == 12
    assert book_checkbox(app, 0).label == "Title 0 — Test Author"
    assert book_checkbox(app, 11).value is False
    assert [item.value for item in app.info] == ["Select at least one book"]
    assert not any(button.label == "Recommend" for button in app.button)
    backend.assert_not_called()


def test_three_selections_react_without_filter_recomputing(ui):
    app, backend = ui
    for index in range(3):
        book_checkbox(app, index).check().run()
    assert not app.exception
    assert app.multiselect[0].value == ["book-0", "book-1", "book-2"]
    assert len(app.dataframe[0].value) == 10
    assert backend.call_count == 3
    backend.assert_called_with(["book-0", "book-1", "book-2"], "popularity", k=10)
    app.text_input[0].set_value("Title 29").run()
    assert len(app.checkbox) == 1
    assert book_checkbox(app, 29).value is False
    assert app.multiselect[0].value == ["book-0", "book-1", "book-2"]
    app.text_input[0].set_value("no matching book").run()
    assert not app.checkbox
    assert backend.call_count == 3
    app.text_input[0].set_value("").run()
    assert all(book_checkbox(app, index).value for index in range(3))
    book_checkbox(app, 1).uncheck().run()
    backend.assert_called_with(["book-0", "book-2"], "popularity", k=10)
    assert backend.call_count == 4
    app.multiselect[0].set_value([]).run()
    assert not app.dataframe
    assert not book_checkbox(app, 0).value
    assert backend.call_count == 4
    assert not app.exception


def test_pagination_and_search_beyond_twenty_results(ui):
    app, backend = ui
    app.text_input[0].set_value("test author").run()
    for _ in range(2):
        next(button for button in app.button if button.label == "Next →").click().run()
    assert book_checkbox(app, 29)
    book_checkbox(app, 29).check().run()
    app.text_input[0].set_value("Title 0").run()
    assert book_checkbox(app, 0)
    assert app.multiselect[0].value == ["book-29"]
    assert backend.call_count == 1
    assert app.session_state["catalog_page"] == 0


def test_limit_and_removal_preserve_checkbox_state(ui):
    app, backend = ui
    for index in range(10):
        book_checkbox(app, index).check().run()
    assert len(app.multiselect[0].value) == 10
    assert book_checkbox(app, 10).disabled
    assert not book_checkbox(app, 0).disabled
    book_checkbox(app, 0).uncheck().run()
    assert not book_checkbox(app, 10).disabled
    app.multiselect[0].set_value(["book-1"]).run()
    assert book_checkbox(app, 1).value
    assert not book_checkbox(app, 2).value
    backend.assert_called_with(["book-1"], "popularity", k=10)
    assert not app.exception


def test_reactive_model_comparison_and_isolated_error(ui):
    app, backend = ui
    book_checkbox(app, 0).check().run()
    success = backend.side_effect

    def mixed(selected, model, k):
        if model == "als":
            return [{"invalid": True}]
        return success(selected, model, k)

    backend.side_effect = mixed
    backend.reset_mock()
    app.toggle[0].set_value(True).run()
    assert app.radio[0].disabled
    assert backend.call_count == 3
    assert [call.args[1] for call in backend.call_args_list] == list(app_service.MODELS)
    assert len(app.dataframe) == 2
    assert len(app.error) == 1
    app.run()
    assert backend.call_count == 3
    app.toggle[0].set_value(False).run()
    assert not app.radio[0].disabled
    assert len(app.dataframe) == 1
    app.radio[0].set_value("itemknn").run()
    backend.assert_called_with(["book-0"], "itemknn", k=10)
    assert not app.exception


def test_fallback_and_session_isolation(ui):
    first, backend = ui
    book_checkbox(first, 0).check().run()
    output = backend.side_effect(["book-0"], "popularity", 10)
    backend.side_effect = [[], output]
    first.radio[0].set_value("itemknn").run()
    assert "fallback popularity" in first.warning[0].value
    second = AppTest.from_file(str(app_service.ROOT / "app.py")).run()
    assert first.session_state["selected"] == ["book-0"]
    assert second.session_state["selected"] == []
    assert not second.dataframe
    assert not first.exception
    assert not second.exception
