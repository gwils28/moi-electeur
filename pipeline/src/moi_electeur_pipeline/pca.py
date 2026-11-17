"""ACP du mode B (SPEC § 5.3, décisions D3 et D4). Voir notebooks/m1-03-acp-mode-b.py."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .engine_ref import project_a

TARGET_MAX = 9.0
TOP_K = 3


def fit_pca(
    election_id: str,
    statements: Sequence[Mapping[str, Any]],
    candidates: Mapping[str, Mapping[str, int | None]],
) -> dict[str, Any]:
    """Calcule le modèle ACP (2 composantes) à partir des positions chargeables des candidats.

    - silences imputés à 0, matrice centrée (moyenne par affirmation) ;
    - composantes = 2 premiers vecteurs singuliers droits ;
    - D3 : signe de la composante k choisi pour corréler positivement avec l'axe k du mode A ;
    - D4 : rescale tel que max |coordonnée candidat| = 9 sur chaque composante.
    """
    ids = [s["id"] for s in statements]
    names = sorted(candidates)
    if len(names) < 3:
        raise ValueError("ACP : au moins 3 candidats sont nécessaires pour 2 composantes.")
    m = np.array([[candidates[c].get(i) or 0 for i in ids] for c in names], dtype=float)
    mean = m.mean(axis=0)
    centered = m - mean
    _, sing, vt = np.linalg.svd(centered, full_matrices=False)
    total = float((sing**2).sum())
    components = vt[:2].copy()
    scores = centered @ components.T

    for k, axis in enumerate(("x", "y")):
        ref = np.array(
            [project_a(candidates[c], statements)[axis] or 0.0 for c in names], dtype=float
        )
        corr = float(np.dot(scores[:, k] - scores[:, k].mean(), ref - ref.mean()))
        # Corrélation nulle : convention de repli, plus forte charge positive.
        if corr < 0 or (corr == 0 and components[k][np.argmax(np.abs(components[k]))] < 0):
            components[k] *= -1
            scores[:, k] *= -1

    max_abs = np.abs(scores).max(axis=0)
    scale = [TARGET_MAX / float(v) if v > 1e-12 else 1.0 for v in max_abs]
    top = [
        [ids[i] for i in np.argsort(-np.abs(components[k]), kind="stable")[:TOP_K]] for k in (0, 1)
    ]
    return {
        "election_id": election_id,
        "statement_ids": ids,
        "mean": [float(v) for v in mean],
        "components": [[float(v) for v in row] for row in components],
        "explained_variance_ratio": [float(s**2 / total) if total else 0.0 for s in sing[:2]],
        "scale": scale,
        "top_statements": top,
    }


def project_b(
    values: Mapping[str, int | None], model: Mapping[str, Any]
) -> tuple[float, float, bool]:
    """Référence Python de projectB (TS) : imputation 0, centrage, rescale, bornage."""
    centered = np.array(
        [
            (values.get(i) or 0) - mu
            for i, mu in zip(model["statement_ids"], model["mean"], strict=True)
        ]
    )
    raw = np.array(model["components"]) @ centered * np.array(model["scale"])
    bounded = np.clip(raw, -10, 10)
    return float(bounded[0]), float(bounded[1]), bool((bounded != raw).any())
