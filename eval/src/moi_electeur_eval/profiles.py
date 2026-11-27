"""Profils synthétiques (PLAN D43, SPEC § 9) : des répondants calqués sur un candidat, avec du
bruit, retrouvent-ils ce candidat en tête de la proximité calculée par le moteur ?

Mesure de la capacité de la boussole à distinguer les programmes, pas de leur valeur. Le calcul
est celui du moteur de référence Python (`engine_ref.proximity`), identique au moteur servi.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import Any

from moi_electeur_pipeline.engine_ref import proximity


@dataclass(frozen=True)
class Noise:
    shift: float = 0.3  # réponse décalée d'un cran
    abstain: float = 0.2  # « sans avis » là où le candidat a une position
    silent_answer: float = 0.5  # réponse au hasard là où le candidat est silencieux


def profile(
    candidate: Mapping[str, int | None], noise: Noise, rng: random.Random
) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for sid, v in candidate.items():
        if v is None:
            out[sid] = rng.randint(-2, 2) if rng.random() < noise.silent_answer else None
        elif rng.random() < noise.abstain:
            out[sid] = None
        elif rng.random() < noise.shift:
            out[sid] = max(-2, min(2, v + rng.choice((-1, 1))))
        else:
            out[sid] = v
    return out


def rank_of(candidate: str, scores: Mapping[str, float | None]) -> int | None:
    """1 + nombre de candidats strictement devant (ex aequo partagés) ; None si non calculable."""
    own = scores.get(candidate)
    if own is None:
        return None
    return 1 + sum(1 for c, s in scores.items() if c != candidate and s is not None and s > own)


def synthetic_profiles(
    answers: Mapping[str, Mapping[str, int | None]],
    statements: Sequence[Mapping[str, Any]],
    *,
    n: int = 200,
    seed: int = 7,
    noise: Noise | None = None,
) -> dict[str, Any]:
    noise = noise or Noise()
    rng = random.Random(seed)
    per: dict[str, dict[str, Any]] = {}
    all_ranks: list[int | None] = []
    for cand in sorted(answers):
        ranks = []
        for _ in range(n):
            user = profile(answers[cand], noise, rng)
            scores = {}
            for other, values in answers.items():
                r = proximity(user, values, statements)
                scores[other] = None if r is None else r["score"]
            ranks.append(rank_of(cand, scores))
        all_ranks.extend(ranks)
        per[cand] = _rates(ranks)
    return {
        "n": n,
        "seed": seed,
        "noise": vars(noise),
        "per_candidate": per,
        "overall": _rates(all_ranks),
    }


def _rates(ranks: Sequence[int | None]) -> dict[str, Any]:
    known = [r for r in ranks if r is not None]
    return {
        "n": len(ranks),
        "top1": fmean(1.0 if r == 1 else 0.0 for r in known) if known else 0.0,
        "top3": fmean(1.0 if r <= 3 else 0.0 for r in known) if known else 0.0,
        "mean_rank": round(fmean(known), 2) if known else None,
    }
