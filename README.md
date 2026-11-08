# Kindle Book Recommender

**▶ Open the app: https://kindle-books-recommender-system.streamlit.app**

Just open the link in any browser — nothing to install, no login needed.
(If the app has been idle for a while, click **Yes, get this app back up!**
and wait about 30 seconds.)

## How to use it

1. Tick 1 to 10 books you like (you can search by title or author).
2. Choose a recommendation model: **Popularity**, **ItemKNN** or **ALS** —
   or switch on **Compare all models at once**.
3. The 10 recommended books appear automatically below.

**Note:** this is a demo version (v0.1.0). The catalog contains 30 fictional
books and the recommendations come from a temporary placeholder backend
(`recommender.py`), not from real trained models or Amazon data.

---

## For developers

### Running locally

Requires Python 3.11–3.14. From the project folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt     # Windows: .venv\Scripts\pip ...
.venv/bin/streamlit run app.py                    # Windows: .venv\Scripts\streamlit ...
```

Then open `http://localhost:8501`. Run the tests with `.venv/bin/pytest -q`.

### Updating the live app

The live app is hosted for free on
[Streamlit Community Cloud](https://share.streamlit.io/) and is built directly
from the `main` branch of this repository. Every `git push` to `main`
redeploys it automatically. If old results persist after a data or backend
change, use **Manage app → ⋮ → Reboot app** in Streamlit Cloud.

## Connecting real models later

1. Replace the temporary `recommender.py` with the delivered, tested module:
   `recommend(liked_asins: list[str], model: str, k: int = 10) -> list[dict]`.
   Models have the keys `popularity`, `itemknn`, `als`. The backend returns books
   in final order with `parent_asin`, `title`, `author`, `genre`, `score`.
2. Replace the demo catalog and add the required item artifacts to `artifacts/`.
   The catalog has `parent_asin` (or `ID`), `title`, `author`, `genre`.
   IDs are unique strings. Add pinned dependencies as required by the backend.
3. Replace `expected_outputs.json` with three real reference cases:
   `{"cases": [{"liked_asins": ["..."], "model": "als", "expected": [...]}]}`.
   `expected` contains complete dictionaries, not just identifiers.
4. Restart the app so the caches are refreshed. A backend without the
   `IS_DEMO = True` flag does not use the demo description in the optional
   "About" expander. Models are registered centrally in
   `app_service.MODELS`; the comparison uses all registered keys without changing
   the number of columns in the UI. Verify the reference outputs and the warm
   response time (target ~2 s).
5. After final verification and public deployment, create a release/tag `v0.1.0`.
   Make further changes in a separate branch only after evaluation.

The app recommends only by calling `recommend()`; it does not model anything and
does not recompute rankings or scores. An empty result or a failure of a
personalised backend triggers `recommend(..., "popularity", k=10)` with a visible
warning. Invalid outputs, selected/duplicate books and books outside the catalog
are not presented as a success. If the backend returns fewer than 10 books,
the UI says so.

## Data and limitations

Currently synthetic books only. Future source:
[Amazon Reviews'23, Kindle Store](https://amazon-reviews-2023.github.io/);
approximately the 20 thousand most popular books, data up to September 2023,
with both the selection and recommendations drawn only from the catalog.

`.gitignore` allows only specific required files. When adding further artifacts,
add their exact paths to the allowlist. No raw reviews, user IDs, user factors,
passwords or keys. No accounts, book covers, click tracking or A/B tests.
