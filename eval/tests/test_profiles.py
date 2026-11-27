"""Profils synthétiques (PLAN D43) : répondants bruités tirés des positions d'un candidat."""

from __future__ import annotations

from moi_electeur_eval.profiles import Noise, profile, rank_of, synthetic_profiles

STATEMENTS = [
    {"id": f"s{i:02d}", "theme": "t", "axis": "x", "direction": 1, "weight_in_axis": 1.0}
    for i in range(1, 9)
]
ANSWERS = {
    "a": {s["id"]: 2 for s in STATEMENTS},
    "b": {s["id"]: -2 for s in STATEMENTS},
    "c": {s["id"]: (0 if i % 2 else None) for i, s in enumerate(STATEMENTS)},
}


def test_profil_sans_bruit_identique_au_candidat() -> None:
    import random

    p = profile(ANSWERS["c"], Noise(shift=0, abstain=0, silent_answer=0), random.Random(1))
    assert p == ANSWERS["c"]


def test_rang_ex_aequo_partage() -> None:
    assert rank_of("a", {"a": 90.0, "b": 90.0, "c": 50.0}) == 1
    assert rank_of("c", {"a": 90.0, "b": 90.0, "c": 50.0}) == 3
    assert rank_of("a", {"a": None, "b": 10.0}) is None


def test_synthese_deterministe_et_plausible() -> None:
    out = synthetic_profiles(ANSWERS, STATEMENTS, n=50, seed=7)
    assert out == synthetic_profiles(ANSWERS, STATEMENTS, n=50, seed=7)
    assert out["per_candidate"]["a"]["top1"] > 0.9
    assert out["per_candidate"]["b"]["top1"] > 0.9
    assert 0 <= out["overall"]["top1"] <= out["overall"]["top3"] <= 1
    assert out["per_candidate"]["a"]["n"] == 50
