"""Fusion RRF et classement thématique (fonctions pures, PLAN § 4.4 et D16)."""

from __future__ import annotations

import numpy as np
import pytest

from moi_electeur_rag.ranking import classify_themes, rrf


def test_rrf_calcule_a_la_main() -> None:
    # a : rangs 1 et 3 -> 1/61 + 1/63 ; b : rang 2 et 1 -> 1/62 + 1/61 ; c : rang 3 seul.
    fused = rrf([["a", "b", "c"], ["b", "x", "a"]], k=60)
    scores = dict(fused)
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 63)
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["c"] == pytest.approx(1 / 63)
    assert scores["x"] == pytest.approx(1 / 62)
    assert [i for i, _ in fused] == ["b", "a", "x", "c"]


def test_rrf_departage_les_egalites_par_identifiant() -> None:
    assert [i for i, _ in rrf([["z"], ["a"]])] == ["a", "z"]


def test_rrf_liste_vide() -> None:
    assert rrf([[], []]) == []


def test_rrf_un_seul_classement_garde_lordre() -> None:
    assert [i for i, _ in rrf([["c", "a", "b"]])] == ["c", "a", "b"]


def _unit(v: list[float]) -> np.ndarray:
    a = np.array(v, dtype=np.float32)
    return a / np.linalg.norm(a)


def test_classify_themes_prend_le_plus_proche() -> None:
    themes = np.stack([_unit([1, 0, 0]), _unit([0, 1, 0])])
    chunks = np.stack([_unit([0.9, 0.1, 0]), _unit([0.1, 0.9, 0.1])])
    assert classify_themes(chunks, themes, ["eco", "social"], margin=0.05) == ["eco", "social"]


def test_classify_themes_null_si_ambigu() -> None:
    themes = np.stack([_unit([1, 0, 0]), _unit([0, 1, 0])])
    chunks = np.stack([_unit([1, 1, 0])])
    assert classify_themes(chunks, themes, ["eco", "social"], margin=0.05) == [None]


def test_classify_themes_sans_theme() -> None:
    chunks = np.stack([_unit([1, 0, 0])])
    assert classify_themes(chunks, np.zeros((0, 3), dtype=np.float32), [], margin=0.05) == [None]
