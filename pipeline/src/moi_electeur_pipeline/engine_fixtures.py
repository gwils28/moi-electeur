"""Fixture croisée `schemas/fixtures/engine_cases.json` : résultats de la référence Python
sur la démo, que les tests Vitest du moteur TS doivent reproduire (PLAN § 1 bis)."""

from __future__ import annotations

import random
from typing import Any

from .demo import build_demo
from .engine_ref import candidate_answers, project_a, proximity

SEED = 7
N_USERS = 4


def build_engine_cases() -> dict[str, Any]:
    demo = build_demo()
    statements = demo["statements.json"]["statements"]
    positions = demo["positions.json"]["positions"]
    ids = [s["id"] for s in statements]
    themes = [t["id"] for t in demo["election_config.json"]["themes"]]
    candidates = {
        c["id"]: candidate_answers(positions, c["id"], ids)
        for c in demo["election_config.json"]["candidates"]
    }
    rng = random.Random(SEED)
    users = []
    for _ in range(N_USERS):
        answers = {i: rng.choice([-2, -1, 0, 1, 2, None]) for i in ids}
        weights = {t: rng.choice([1, 2, 3]) for t in themes}
        users.append(
            {
                "answers": answers,
                "weights": weights,
                "point": project_a(answers, statements),
                "proximity": {
                    c: proximity(answers, a, statements, weights) for c, a in candidates.items()
                },
            }
        )
    return {
        "description": "Généré par `uv run pipeline engine-fixtures` (référence Python). Ne pas éditer.",
        "statements": statements,
        "candidates": {
            c: {"answers": a, "point": project_a(a, statements)} for c, a in candidates.items()
        },
        "users": users,
    }
