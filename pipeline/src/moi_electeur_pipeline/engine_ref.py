"""Implémentation de référence Python des formules du moteur (SPEC § 5.3).

Sert au pipeline (orientation de l'ACP, décision D3) et aux notebooks. Le moteur servi
au navigateur reste `packages/engine` (TS) ; la cohérence est vérifiée sur des fixtures communes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

LOADED_STATUSES = frozenset({"validated", "corrected"})


def candidate_answers(
    positions: Sequence[Mapping[str, Any]], candidate_id: str, statement_ids: Sequence[str]
) -> dict[str, int | None]:
    """Positions chargeables d'un candidat ; tout le reste est un silence (None)."""
    out: dict[str, int | None] = dict.fromkeys(statement_ids)
    for p in positions:
        if (
            p["candidate_id"] == candidate_id
            and p["statement_id"] in out
            and p["review"]["status"] in LOADED_STATUSES
        ):
            out[p["statement_id"]] = p["value"]
    return out


def project_a(
    values: Mapping[str, int | None], statements: Sequence[Mapping[str, Any]]
) -> dict[str, float | None]:
    """Mode A : 10 · Σ w·dir·v / Σ w·2 par axe, silences exclus ; None si l'axe est vide."""
    out: dict[str, float | None] = {}
    for axis in ("x", "y"):
        num = den = 0.0
        for s in statements:
            v = values.get(s["id"])
            if s["axis"] != axis or v is None:
                continue
            num += s["weight_in_axis"] * s["direction"] * v
            den += s["weight_in_axis"] * 2
        out[axis] = None if den == 0 else 10 * num / den
    return out


def proximity(
    user: Mapping[str, int | None],
    candidate: Mapping[str, int | None],
    statements: Sequence[Mapping[str, Any]],
    weights: Mapping[str, float] | None = None,
) -> dict[str, Any] | None:
    """Référence de `proximity` (SPEC § 5.2)."""
    weights = weights or {}
    d = d_max = 0.0
    n = answered = 0
    for s in statements:
        u, c = user.get(s["id"]), candidate.get(s["id"])
        if u is None:
            continue
        answered += 1
        if c is None:
            continue
        w = weights.get(s["theme"], 1)
        d += w * abs(u - c)
        d_max += w * 4
        n += 1
    if n == 0:
        return None
    coverage = n / answered
    return {
        "score": 100 * (1 - d / d_max),
        "coverage": coverage,
        "n": n,
        "answered": answered,
        "lowCoverage": coverage < 0.5,
    }
