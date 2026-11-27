"""Neutralité par permutation (PLAN D41, SPEC § 9) : la même question posée avec plusieurs
tirages de l'ordre des candidats. Un chat neutre donne à chaque candidat une section de taille
comparable quel que soit son rang de présentation ; l'effet de rang se lit dans la corrélation
de Spearman entre rang et longueur, et la stabilité de chaque candidat dans le coefficient de
variation de sa longueur d'un tirage à l'autre.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from statistics import fmean, pstdev
from typing import Any

from .chat import is_silence, parse_answer
from .stats import spearman


def permutation_effects(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    ranks: list[float] = []
    lengths: list[float] = []
    by_rank: dict[int, dict[str, list[float]]] = {}
    per_candidate: dict[tuple[str, str], list[float]] = {}
    answers = 0
    questions = set()
    for r in records:
        if r["status"] != 200:
            continue
        answer = parse_answer(r["events"])
        answers += 1
        questions.add(r["question_id"])
        for rank, cand in enumerate(answer.candidates, 1):
            section = answer.sections.get(cand)
            if section is None or is_silence(section.text):
                continue
            n = float(len(section.text))
            ranks.append(rank)
            lengths.append(n)
            slot = by_rank.setdefault(rank, {"length": [], "citations": []})
            slot["length"].append(n)
            slot["citations"].append(float(len(section.citations)))
            per_candidate.setdefault((r["question_id"], cand), []).append(n)
    cv: dict[str, list[float]] = {}
    for (_, cand), values in per_candidate.items():
        if len(values) >= 2 and fmean(values) > 0:
            cv.setdefault(cand, []).append(pstdev(values) / fmean(values))
    return {
        "answers": answers,
        "questions": len(questions),
        "by_rank": {
            rank: {
                "length": fmean(v["length"]),
                "citations": fmean(v["citations"]),
                "n": len(v["length"]),
            }
            for rank, v in sorted(by_rank.items())
        },
        "spearman_rank_length": spearman(ranks, lengths) if len(ranks) >= 2 else None,
        "per_candidate_cv": {c: fmean(v) for c, v in sorted(cv.items())},
    }
