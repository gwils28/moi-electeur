"""Fusion RRF et classement thématique : fonctions pures, testées sur des cas calculés à la main."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

RRF_K = 60


def rrf(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion : score = somme des 1 / (k + rang), rang à partir de 1.

    Tri par score décroissant puis identifiant (déterministe).
    """
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def classify_themes(
    chunks: npt.NDArray[np.float32],
    themes: npt.NDArray[np.float32],
    theme_ids: Sequence[str],
    margin: float,
) -> list[str | None]:
    """Thème le plus proche (cosinus, vecteurs normalisés) ; None si l'écart avec le second
    est inférieur à `margin` (cas ambigu, PLAN D16)."""
    if len(theme_ids) == 0:
        return [None] * len(chunks)
    sims = chunks @ themes.T
    out: list[str | None] = []
    for row in sims:
        order = np.argsort(-row)
        best = float(row[order[0]])
        second = float(row[order[1]]) if len(order) > 1 else -1.0
        out.append(theme_ids[int(order[0])] if best - second >= margin else None)
    return out
