# Kindle Book Recommender — frontend demo v0.1.0

A Streamlit interface and infrastructure for picking 1 to 10 favourite books,
choosing a model (Popularity / ItemKNN / ALS) and displaying 10 recommendations:
rank, title, author, genre. It features a visible book list with checkboxes,
a live filter by title/author, removal of selected books, a limit of 10,
validation and an explicit fallback.

**Current scope:** frontend and platform, not model development. The catalog
contains 30 fictional books. `recommender.py` is only a temporary deterministic
random backend for trying out the whole interface. These are not real models
and not Amazon data.

The **Compare all models at once** toggle shows
the models side by side. Each model receives the same book selection and keeps
its own ranking, fallback warning or error; results are not combined. Individual
model selection is disabled in this mode. Changing the selection, model or mode
refreshes the recommendations automatically, without a confirm button. Filtering
or paging alone does not call the backend again. An empty selection clears the
results.

## Running the app

Requirements: **Python 3.11 – 3.14** and `git` (optional). No login, API keys
or external services are needed. The bundled demo data is in
`artifacts/catalog.parquet`; nothing has to be trained or downloaded.

Always run the commands from the project root (the folder containing `app.py`).

### macOS / Linux (Terminal)

```bash
cd path/to/Kindle-Books-Recommender-System

# First time only: create a virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt

# Start the app
.venv/bin/python -m streamlit run app.py
```

### Windows (PowerShell)

```powershell
Set-Location -LiteralPath 'C:\path\to\Kindle-Books-Recommender-System'

# First time only: create a virtual environment and install dependencies
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# Start the app
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Then open `http://localhost:8501` in your browser (the server runs headless,
so the browser does not open automatically). Stop the app with `Ctrl+C`.

Notes:

- `requirements.txt` contains only the runtime dependencies;
  `requirements-dev.txt` adds `pytest` for the tests.
- A `.venv` folder copied from another computer (e.g. created on Windows)
  will not work on macOS/Linux and vice versa — delete it and create a new one.
- If you have several Python versions installed, select one explicitly, e.g.
  `python3.12 -m venv .venv` (macOS/Linux) or `py -3.12 -m venv .venv` (Windows).
  Python 3.10 and older are not supported by the pinned `numpy` version.
- Streamlit telemetry is disabled. If the backend/catalog is missing, the app
  shows an explanation; if a recommendation fails, it shows a message and the
  diagnostics are written to the server log.

## Selecting books

Tick 1 to 10 books directly in the list (rows have a subtly alternating colour).
The selection is preserved while searching and paging. Remove a book by
unticking it or by clicking × in the selected books. Once 10 books are selected,
the remaining checkboxes are disabled until you remove one of the selected books.

The `streamlit-keyup==0.4.0` filter sends the text on input change with a 250 ms
debounce: the list refreshes after a short pause in typing, without pressing
Enter or leaving the field. It does not respond instantly to every character
during continuous fast typing. The component uses the `input` event, so it also
reacts to pasted text. It searches for a literal, case-insensitive substring of
the title or author. It shows 12 books per page; all matches are available on
subsequent pages. A new filter starts on the first page.

## Local validation

Streamlit has no separate frontend build step. Basic checks of the Python code,
dependency consistency and the small existing test suite:

macOS / Linux:

```bash
.venv/bin/python -m compileall -q app.py app_service.py recommender.py tests
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m compileall -q app.py app_service.py recommender.py tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

AppTest covers the visible list, selecting three books, paging, preserving the
selection while filtering, the limit of 10, reactive recommendations, comparison
and fallback. In AppTest only the component's input boundary is replaced by a
native text field; the tests do not prove real typing events or browser
debounce. `expected_outputs.json` contains three fixed reference inputs and the
complete demo outputs. The test verifies exact match, determinism, 10 results,
presence in the catalog and exclusion of the selected books. The demo tests do
not verify the quality or speed of future models.

## Public deployment: Streamlit Community Cloud (free)

The app is hosted for free on Streamlit Community Cloud
(`https://share.streamlit.io/`), which builds it directly from this GitHub
repository. Anyone with the link can open it in a browser — no installation,
no login.

### First deployment (one-time)

1. Make sure all files are pushed to GitHub
   (`https://github.com/janosova5/Kindle-Books-Recommender-System`, branch `main`).
2. Go to `https://share.streamlit.io/` and sign in with **Continue with GitHub**
   (authorise Streamlit to access your repositories).
3. Click **Create app** → **Deploy a public app from GitHub**.
4. Fill in:
   - **Repository:** `janosova5/Kindle-Books-Recommender-System`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** choose a name, e.g. `kindle-books-recommender`
     (the app will be at `https://kindle-books-recommender.streamlit.app`)
5. Open **Advanced settings** and select **Python 3.12** (3.11–3.14 also work).
   No secrets are needed.
6. Click **Deploy**. The first build takes a few minutes
   (it installs `requirements.txt`).
7. Make sure the app is public: in the app's **Settings → Sharing** set
   *Who can view this app* to **This app is public and searchable**.
   Verify the link in a private/incognito browser window.

### Updates

Every `git push` to `main` redeploys the app automatically within a minute or
so. If the data or backend changed and old results persist, use
**Manage app → ⋮ → Reboot app** to clear the caches.

Notes: free apps go to sleep after a period without visitors; the first visitor
then clicks **Yes, get this app back up!** and waits ~30 s. A single Streamlit
process calls the Python backend directly — no Docker, separate API, database
or custom authentication. The theme and disabled telemetry are in
`.streamlit/config.toml`. The catalog and backend are loaded via the Streamlit
cache; each visitor's selection and results live only in their own
`st.session_state`, and nothing is written to disk.

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
