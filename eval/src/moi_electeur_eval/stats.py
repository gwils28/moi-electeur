"""Statistiques du backtest (PLAN § 6, M4). Sans dépendance au-delà de numpy."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

SEED = 7


def paired_bootstrap(
    a: Sequence[float], b: Sequence[float], *, seed: int = SEED, n: int = 10_000
) -> tuple[float, float, float]:
    """Écart moyen a - b et son intervalle à 95 % (questions rééchantillonnées avec remise)."""
    if len(a) != len(b) or not a:
        raise ValueError("listes appariées de même longueur non vide attendues")
    diff = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    rng = np.random.default_rng(seed)
    means = diff[rng.integers(0, len(diff), size=(n, len(diff)))].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(diff.mean()), float(lo), float(hi)


def weighted_kappa(
    a: Sequence[int], b: Sequence[int], *, categories: Sequence[int] = (-2, -1, 0, 1, 2)
) -> float:
    """Kappa de Cohen à poids quadratiques (accord sur une échelle ordinale)."""
    if len(a) != len(b) or not a:
        raise ValueError("listes appariées de même longueur non vide attendues")
    index = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    observed = np.zeros((k, k))
    for x, y in zip(a, b, strict=True):
        observed[index[x], index[y]] += 1
    observed /= observed.sum()
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0))
    i, j = np.indices((k, k))
    weights = (i - j) ** 2 / (k - 1) ** 2
    denominator = (weights * expected).sum()
    if denominator == 0:
        return float("nan")
    return float(1 - (weights * observed).sum() / denominator)


def _ranks(values: Sequence[float]) -> np.ndarray:
    v = np.asarray(values, dtype=np.float64)
    order = v.argsort(kind="mergesort")
    ranks = np.empty(len(v))
    ranks[order] = np.arange(1, len(v) + 1)
    for value in np.unique(v):  # rangs moyens pour les ex aequo
        tied = v == value
        ranks[tied] = ranks[tied].mean()
    return ranks


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Corrélation de rangs de Spearman (rangs moyens pour les ex aequo) ; nan si constante."""
    if len(a) != len(b) or len(a) < 2:
        raise ValueError("au moins deux couples appariés attendus")
    ra, rb = _ranks(a), _ranks(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])
