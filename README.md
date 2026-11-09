# Kindle Book Recommender

**▶ Open the app: https://kindle-books-recommender-system.streamlit.app**

Just open the link in any browser — nothing to install, no login needed.
(If the app has been idle for a while, click **Yes, get this app back up!**
and wait about 30 seconds.)

## How to use it

1. Tick 1 to 10 books you like (you can search by title or author). They are
   listed under **Your selection**, where you can remove them with ✕.
2. Click **Confirm selection**.
3. Choose a recommendation model: **Popularity**, **ItemKNN** or **ALS** —
   or switch on **Compare all models at once**.
4. Click **Get recommendations** to see the 10 recommended books.

The catalog contains the **30,000 most popular Kindle books** from the
[Amazon Reviews'23](https://amazon-reviews-2023.github.io/) dataset.

| Model | What it recommends |
|---|---|
| **Popularity** | The most popular books, without personalisation |
| **ItemKNN** | Books similar to the ones you selected (item-item similarity) |
| **ALS** | Personalised recommendations based on latent factors |

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

### How it fits together

- `app.py` — the Streamlit user interface.
- `app_service.py` — input validation, output checks and the popularity
  fallback; it does not compute recommendations itself.
- `recommender.py` — the trained models; `recommend(liked_asins, model, k=10)`
  returns books with `parent_asin`, `title`, `author`, `genre`, `score`
  (plus `rank` and `fallback`, which the app ignores except for showing a
  fallback warning).
- `artifacts/` — the model files exported from the training notebook:
  `catalog.parquet`, `popularity.json`, `itemknn_sim.npz`,
  `als_item_factors.npy`, `model_params.json` (hyperparameters and library
  versions) and `expected_outputs.json` (the notebook's reference outputs).
- `expected_outputs.json` (root) — the same 9 reference cases with full book
  records; the tests check that the app returns exactly these.

To update the models, re-export the files above from the notebook, keep the
library versions in `requirements.txt` in sync with `model_params.json`, run
the tests, and push to `main`.

## Data and limitations

Source: [Amazon Reviews'23, Kindle Store](https://amazon-reviews-2023.github.io/).
The models were trained on ratings before 2023-01-01; the catalog holds the
30,000 most popular books, and both the selection and the recommendations come
only from this catalog.

`.gitignore` allows only specific required files. When adding further artifacts,
add their exact paths to the allowlist. No raw reviews, user IDs, user factors,
passwords or keys are stored in the repository.
