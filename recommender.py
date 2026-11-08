"""Temporary deterministic demo backend; replace with the supplied recommender."""

from functools import lru_cache
import hashlib
from pathlib import Path
import random

import pandas as pd


IS_DEMO = True
DEMO_BOOKS = [
    ("Moonlit Harbor", "Alex Reed", "Mystery"),
    ("The Clockwork Garden", "Robin Vale", "Fantasy"),
    ("Beyond the Copper Sky", "Sam Rowan", "Sci-Fi"),
    ("Letters from Willow Bay", "Jamie Brook", "Drama"),
    ("The Last Paper Train", "Morgan Lake", "Adventure"),
    ("Summer on Lantern Street", "Casey Hart", "Comedy"),
    ("Echoes of the Glass Mountain", "Taylor Ash", "Fantasy"),
    ("A Map of Tomorrow", "Jordan Pine", "Sci-Fi"),
    ("Midnight at Cedar Station", "Avery Stone", "Mystery"),
    ("The Quiet Orchestra", "Riley West", "Drama"),
    ("Seven Clouds to Home", "Alex Reed", "Adventure"),
    ("The Pancake Expedition", "Robin Vale", "Comedy"),
    ("Orbit of the Blue Kite", "Sam Rowan", "Sci-Fi"),
    ("Where the River Sleeps", "Jamie Brook", "Drama"),
    ("The Umbrella Detective", "Morgan Lake", "Mystery"),
    ("A Castle Made of Rain", "Casey Hart", "Fantasy"),
    ("The Unlikely Lighthouse", "Taylor Ash", "Comedy"),
    ("Footprints on Saturn", "Jordan Pine", "Sci-Fi"),
    ("The Amber Compass", "Avery Stone", "Adventure"),
    ("Spring behind the Window", "Riley West", "Drama"),
    ("The Missing Tuesday", "Alex Reed", "Mystery"),
    ("Dreams of the Silver Fox", "Robin Vale", "Fantasy"),
    ("A Rocket for Two", "Sam Rowan", "Comedy"),
    ("The Valley of Small Stars", "Jamie Brook", "Adventure"),
    ("When the Bells Turn Blue", "Morgan Lake", "Drama"),
    ("The Secret of Maple Lane", "Casey Hart", "Mystery"),
    ("Cloudkeeper's Journey", "Taylor Ash", "Fantasy"),
    ("The Far Side of Morning", "Jordan Pine", "Sci-Fi"),
    ("The Bicycle Parliament", "Avery Stone", "Comedy"),
    ("Across the Violet Sea", "Riley West", "Adventure"),
]


def demo_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "parent_asin": f"DEMO-{index:03}",
                "title": title,
                "author": author,
                "genre": genre,
            }
            for index, (title, author, genre) in enumerate(DEMO_BOOKS, 1)
        ]
    )


@lru_cache(maxsize=1)
def _catalog() -> list[dict]:
    path = Path(__file__).resolve().parent / "artifacts" / "catalog.parquet"
    return pd.read_parquet(path).to_dict("records")


def recommend(liked_asins: list[str], model: str, k: int = 10) -> list[dict]:
    if model not in {"popularity", "itemknn", "als"}:
        raise ValueError("Unknown demo generator")
    if k < 1:
        raise ValueError("k must be positive")
    selected = set(liked_asins)
    catalog = _catalog()
    if not selected.issubset({movie["parent_asin"] for movie in catalog}):
        raise ValueError("Selected book is not in the demo catalog")
    candidates = [book for book in catalog if book["parent_asin"] not in selected]
    seed_input = model + "|" + "|".join(sorted(selected))
    seed = int.from_bytes(hashlib.sha256(seed_input.encode("utf-8")).digest(), "big")
    rng = random.Random(seed)
    count = min(k, len(candidates))
    if model == "popularity":
        chosen = rng.sample(candidates, count)
    elif model == "itemknn":
        rng.shuffle(candidates)
        chosen = candidates[:count]
    else:
        chosen = sorted(candidates, key=lambda book: rng.random())[:count]
    return [
        {**book, "score": float(len(chosen) - rank)}
        for rank, book in enumerate(chosen)
    ]
