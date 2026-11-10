# Kindle Book Recommender

**▶ Open the app: https://kindle-books-recommender-system.streamlit.app**

A web app that recommends Kindle books to readers looking for their next
read. It is a school project for the course *Modelling in Data Science*.

## What it does

1. Select 1–10 books you like. You can search by title or author.
2. Click **Confirm selection**.
3. Choose a model, or switch on **Compare all models at once**.
4. Click **Get recommendations** to see **10 recommended books**.

| Model | What it recommends |
|---|---|
| **Popularity** | The most popular books, without personalisation |
| **ItemKNN** | Books similar to the ones you selected (item–item similarity, k = 100) |
| **ALS** | Personalised recommendations from latent factors (1024 factors, λ = 1, α = 200) |

If a model cannot score your selection, the app shows popular books instead
and says so in a short note.

## Models and data

- The models are trained on ratings from **Amazon Reviews'23, Kindle Store
  (5-core)** given **before 2023**.
- The catalog contains the **30,000 books with the most ratings in the last
  12 months of the training period**. Both the selection and the
  recommendations come only from this catalog.
- Data source: [Amazon Reviews'23](https://amazon-reviews-2023.github.io)
  (Hou et al., 2024). This repository contains only derived model files in
  `artifacts/`, not the raw reviews.

## Running locally

Requires Python 3.11 or later.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open `http://localhost:8501`.

## Running the tests

```bash
pytest -q
```

## Project structure

- `app.py`: the Streamlit user interface.
- `app_service.py`: input validation and output checks. Recommendations
  come only from `recommender.recommend(liked_asins, model, k)` and search
  only from `recommender.search(text, limit)`.
- `recommender.py`: loads the trained models and computes recommendations.
- `artifacts/`: `catalog.parquet`, `popularity.json`, `itemknn_sim.npz`,
  `als_item_factors.npy`, `model_params.json` and `expected_outputs.json`
  (reference outputs from the training notebook, checked by the tests).

The live app is hosted on Streamlit Community Cloud and redeploys
automatically after each push to `main`.
