"""Statistiques du backtest (M4) : bootstrap apparié, kappa pondéré, Spearman."""

from __future__ import annotations

import math

import pytest

from moi_electeur_eval.stats import paired_bootstrap, spearman, weighted_kappa


def test_bootstrap_apparie_deterministe_et_centre() -> None:
    a = [0.5, 0.6, 0.7, 0.8, 0.9] * 4
    b = [x - 0.1 for x in a]
    mean, lo, hi = paired_bootstrap(a, b, seed=7)
    assert mean == pytest.approx(0.1)
    assert lo == pytest.approx(0.1) and hi == pytest.approx(0.1)  # écart constant
    assert paired_bootstrap(a, b, seed=7) == (mean, lo, hi)


def test_bootstrap_intervalle_contient_zero_si_ecart_nul() -> None:
    a = [0.1, 0.9, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8]
    b = [0.9, 0.1, 0.6, 0.4, 0.7, 0.3, 0.8, 0.2]
    _, lo, hi = paired_bootstrap(a, b, seed=7)
    assert lo < 0 < hi


def test_bootstrap_refuse_des_listes_inegales() -> None:
    with pytest.raises(ValueError):
        paired_bootstrap([1.0], [1.0, 2.0])


def test_kappa_pondere() -> None:
    assert weighted_kappa([-2, -1, 0, 1, 2], [-2, -1, 0, 1, 2]) == pytest.approx(1.0)
    # Désaccord total et symétrique : kappa négatif.
    assert weighted_kappa([-2, -2, 2, 2], [2, 2, -2, -2]) < 0
    # Écart d'un cran partout : accord partiel, inférieur à 1.
    k = weighted_kappa([-2, -1, 0, 1], [-1, 0, 1, 2])
    assert 0 < k < 1


def test_spearman() -> None:
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert spearman([1, 2, 2, 3], [1, 2, 3, 4]) == pytest.approx(0.9486833, rel=1e-6)
    assert math.isnan(spearman([1, 1, 1], [1, 2, 3]))
