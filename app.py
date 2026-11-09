"""Kindle Book Recommender v0.1.0 Streamlit UI."""

import logging

import pandas as pd
import streamlit as st
from st_keyup import st_keyup

from app_service import (
    InputError,
    MODELS,
    backend_is_demo,
    get_backend,
    load_catalog,
    recommend_books,
    search_books,
    validate_selection,
)


st.set_page_config(page_title="Kindle Book Recommender", page_icon="📚", layout="wide")
st.title("Kindle Book Recommender")


@st.cache_data(show_spinner=False)
def cached_catalog():
    return load_catalog()


@st.cache_resource(show_spinner=False)
def cached_backend():
    return get_backend()


try:
    catalog = cached_catalog()
    backend = cached_backend()
    is_demo = backend_is_demo()
except Exception:
    logging.getLogger(__name__).exception("Application initialization failed")
    st.error(
        "The app is not ready yet. Provide recommender.py and the complete "
        "artifacts/ folder including catalog.parquet. Details are in the server log."
    )
    st.stop()

with st.expander("About"):
    if is_demo:
        st.write(
            "The demo catalog contains fictional books. Recommendations come from "
            "a temporary deterministic backend, not from trained models."
        )
    else:
        st.write("A school project recommending books from the connected catalog.")

if "selected" not in st.session_state:
    st.session_state.selected = []
if "confirmed" not in st.session_state:
    st.session_state.confirmed = False

PAGE_SIZE = 12
MAX_BOOKS = 10
labels = dict(
    zip(catalog["parent_asin"], catalog["title"] + " — " + catalog["author"])
)


def toggle_book(asin):
    selected = st.session_state.selected.copy()
    if st.session_state[f"book_{asin}"]:
        if asin not in selected and len(selected) < MAX_BOOKS:
            selected.append(asin)
    elif asin in selected:
        selected.remove(asin)
    st.session_state.selected = selected


def remove_book(asin):
    st.session_state.selected = [
        item for item in st.session_state.selected if item != asin
    ]


def clear_books():
    st.session_state.selected = []


def set_confirmed(value):
    st.session_state.confirmed = value
    st.session_state.pop("result", None)


def change_page(offset):
    st.session_state.catalog_page += offset


selection = st.session_state.selected.copy()
if not selection:
    st.session_state.confirmed = False
confirmed = st.session_state.confirmed

st.subheader("1. Your favourite books")

if confirmed:
    st.success(f"Selection confirmed: {len(selection)} book(s)")
    for number, asin in enumerate(selection, 1):
        st.markdown(f"{number}. {labels[asin]}")
    st.button("← Edit selection", on_click=set_confirmed, args=(False,))
else:
    catalog_column, selection_column = st.columns([3, 2], gap="large")

    with catalog_column:
        query = st_keyup(
            "Search by title or author",
            max_chars=200,
            debounce=250,
            key="catalog_search",
            placeholder="Title or author",
        )
        query = (query or "").strip()
        if query != st.session_state.get("catalog_query"):
            st.session_state.catalog_query = query
            st.session_state.catalog_page = 0
        matches = search_books(catalog, query, limit=None) if query else catalog
        page_count = max(1, (len(matches) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(st.session_state.get("catalog_page", 0), page_count - 1)
        st.session_state.catalog_page = page
        st.caption(f"Books found: {len(matches)}")

        st.html("""
<style>
[class*="st-key-catalog_even_"], [class*="st-key-catalog_odd_"] {
    padding: 0.35rem 0.75rem;
    border-radius: 0.3rem;
}
[class*="st-key-catalog_even_"] {
    background-color: var(--secondary-background-color, #F0EDE7);
}
[class*="st-key-catalog_odd_"] {
    background-color: var(--background-color, #FAF9F6);
}
</style>
""")
        if matches.empty:
            st.info("No books found.")
        for index, book in enumerate(
            matches.iloc[page * PAGE_SIZE : (page + 1) * PAGE_SIZE].to_dict("records")
        ):
            asin = book["parent_asin"]
            key = f"book_{asin}"
            # Hidden widgets are cleaned up by Streamlit; canonical selection survives.
            st.session_state[key] = asin in selection
            stripe = "even" if index % 2 == 0 else "odd"
            with st.container(key=f"catalog_{stripe}_{index}"):
                st.checkbox(
                    labels[asin],
                    key=key,
                    disabled=len(selection) >= MAX_BOOKS and asin not in selection,
                    on_change=toggle_book,
                    args=(asin,),
                )
        if page_count > 1:
            previous, position, following = st.columns([1, 2, 1])
            previous.button(
                "← Previous",
                disabled=page == 0,
                on_click=change_page,
                args=(-1,),
            )
            position.caption(f"Page {page + 1}/{page_count}")
            following.button(
                "Next →",
                disabled=page == page_count - 1,
                on_click=change_page,
                args=(1,),
            )

    with selection_column:
        st.markdown(f"**Your selection ({len(selection)}/{MAX_BOOKS})**")
        if not selection:
            st.info("Select at least one book")
        with st.container(border=True):
            for asin in selection:
                title_column, remove_column = st.columns([6, 1])
                title_column.write(labels[asin])
                remove_column.button(
                    "✕",
                    key=f"remove_{asin}",
                    help="Remove from selection",
                    on_click=remove_book,
                    args=(asin,),
                )
            if not selection:
                st.caption("Nothing selected yet.")
        if selection:
            st.button("Clear all", on_click=clear_books)
        st.button(
            f"Confirm selection ({len(selection)} books) →",
            type="primary",
            disabled=not selection,
            on_click=set_confirmed,
            args=(True,),
            width="stretch",
        )

if not confirmed:
    st.stop()

st.subheader("2. Recommendation method")
compare = st.toggle("Compare all models at once", value=False)
model = st.radio(
    "Model", list(MODELS), format_func=lambda key: MODELS[key][0], horizontal=True,
    disabled=compare,
)
requested_models = tuple(MODELS) if compare else (model,)
request_key = (tuple(selection), requested_models)
for requested_model in requested_models:
    name, description = MODELS[requested_model]
    st.caption(f"{name}: {description}")

if st.button("Get recommendations", type="primary"):
    st.session_state.pop("result", None)
    try:
        selected = validate_selection(selection, requested_models[0])
    except InputError as exc:
        st.warning(str(exc))
    else:
        outcomes = {}
        with st.spinner("Computing recommendations..."):
            for requested_model in requested_models:
                try:
                    result = recommend_books(selected, requested_model, backend)
                    if any(book["parent_asin"] not in labels for book in result.books):
                        raise ValueError("Backend returned a book outside the catalog")
                    outcomes[requested_model] = (result, None)
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Recommendation request failed for model %s", requested_model
                    )
                    outcomes[requested_model] = (
                        None,
                        "Recommendations are currently unavailable. Try another model "
                        "or book selection. Details are in the server log.",
                    )
        st.session_state.result = (request_key, outcomes)

stored = st.session_state.get("result")
if stored and stored[0] != request_key:
    st.info("Settings changed. Click **Get recommendations** to update the results.")
elif stored:
    st.subheader("3. Books for you")
    panels = st.columns(len(requested_models)) if compare else [st.container()]
    for panel, requested_model in zip(panels, requested_models):
        with panel:
            if compare:
                st.subheader(MODELS[requested_model][0])
            result, error = stored[1][requested_model]
            if error:
                st.error(error)
                continue
            if result.warning:
                st.warning(result.warning)
            rows = [
                {
                    "Rank": rank,
                    "Title": book["title"],
                    "Author": book["author"],
                    "Genre": book["genre"],
                }
                for rank, book in enumerate(result.books, 1)
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
