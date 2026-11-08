import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from recommender import MODELS, recommend  # noqa: E402

EXPECTED = json.loads((ROOT / "artifacts" / "expected_outputs.json").read_text())


@pytest.mark.parametrize("case", EXPECTED)
def test_same_as_notebook(case):
    got = [r["parent_asin"] for r in recommend(case["liked"], case["model"], 10)]
    assert got == case["expected"]


@pytest.mark.parametrize("model", MODELS)
def test_excludes_liked_and_is_deterministic(model):
    liked = EXPECTED[0]["liked"]
    a, b = recommend(liked, model, 10), recommend(liked, model, 10)
    assert a == b
    assert len(a) == 10
    assert not set(liked) & {r["parent_asin"] for r in a}


def test_duplicates_are_ignored():
    liked = EXPECTED[0]["liked"]
    assert recommend(liked + liked, "als", 10) == recommend(liked, "als", 10)


@pytest.mark.parametrize("bad", [[], None])
def test_empty_selection(bad):
    with pytest.raises(ValueError, match="at least one"):
        recommend(bad, "als")


def test_unknown_book():
    with pytest.raises(ValueError, match="not in the catalogue"):
        recommend(["NOT_A_BOOK"], "als")


def test_too_many_books():
    from recommender import _load
    asins = list(_load()[0]["parent_asin"][:11])
    with pytest.raises(ValueError, match="at most"):
        recommend(asins, "als")


def test_unknown_model():
    with pytest.raises(ValueError, match="Unknown model"):
        recommend(EXPECTED[0]["liked"], "deep-learning")
