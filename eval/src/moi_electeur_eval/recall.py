"""Rappel@k du retrieval sur le jeu de fumée, sans LLM (PLAN § 4.7, § 4.9).

Définitions (q = question, c = candidat attendu, R = extraits pertinents de c pour q,
L = extraits renvoyés pour c, dans l'ordre) :

- rappel@k(q, c) = |L[:k] ∩ R| / min(k, |R|) : 1 quand les k places sont occupées par des extraits
  pertinents, ou quand tous les pertinents sont présents si |R| < k ;
- succès@k(q, c) = 1 si L[:k] contient au moins un extrait pertinent : sans lui, le modèle de
  langue ne voit rien de pertinent pour ce candidat et risque un faux « Aucune proposition » ;
- rappel@k(q) = moyenne de rappel@k(q, c) sur les candidats attendus ; rappel global (macro) =
  moyenne sur les questions qui ont des attendus ; rappel micro = moyenne sur les couples (q, c) ;
- couverture : chaque candidat indexé reçoit au moins un extrait dans L[:k] (critère PLAN § 4.9).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from statistics import fmean

from .smoke import Question

# rankings[question_id][candidate_id] = identifiants d'extraits, du mieux classé au moins bien.
Rankings = Mapping[str, Mapping[str, Sequence[str]]]


def recall_at_k(ranked: Sequence[str], relevant: Collection[str], k: int) -> float:
    if k < 1:
        raise ValueError("k doit valoir au moins 1")
    if not relevant:
        raise ValueError("rappel indéfini sans extrait pertinent")
    hits = len(set(ranked[:k]) & set(relevant))
    return hits / min(k, len(relevant))


def hit_at_k(ranked: Sequence[str], relevant: Collection[str], k: int) -> bool:
    if k < 1:
        raise ValueError("k doit valoir au moins 1")
    return bool(set(ranked[:k]) & set(relevant))


@dataclass(frozen=True)
class PairScore:
    question_id: str
    candidate_id: str
    recall: float
    hit: bool
    n_relevant: int


@dataclass(frozen=True)
class QuestionScore:
    question_id: str
    kind: str
    recall: float | None  # None : aucune attente (demande de recommandation)
    hit_rate: float | None
    missed: list[str]  # candidats attendus sans aucun extrait pertinent dans les k premiers
    uncovered: list[str]  # candidats indexés sans aucun extrait dans les k premiers


@dataclass(frozen=True)
class MethodReport:
    k: int
    questions: list[QuestionScore]
    pairs: list[PairScore] = field(default_factory=list)

    @property
    def recall(self) -> float:
        values = [q.recall for q in self.questions if q.recall is not None]
        return fmean(values) if values else float("nan")

    @property
    def recall_micro(self) -> float:
        return fmean(p.recall for p in self.pairs) if self.pairs else float("nan")

    @property
    def hit_rate(self) -> float:
        return fmean(1.0 if p.hit else 0.0 for p in self.pairs) if self.pairs else float("nan")

    @property
    def full_coverage(self) -> bool:
        return all(not q.uncovered for q in self.questions)


def evaluate(
    questions: Sequence[Question],
    rankings: Rankings,
    candidates: Collection[str],
    k: int = 4,
) -> MethodReport:
    """Score d'une méthode (un modèle, une façon de classer) sur le jeu de fumée."""
    scores: list[QuestionScore] = []
    pairs: list[PairScore] = []
    for q in questions:
        per_candidate = rankings.get(q.id, {})
        uncovered = sorted(c for c in candidates if not per_candidate.get(c, [])[:k])
        q_pairs = []
        for cand in sorted(q.expected):
            ranked = per_candidate.get(cand, [])
            relevant = q.relevant(cand)
            q_pairs.append(
                PairScore(
                    q.id,
                    cand,
                    recall_at_k(ranked, relevant, k),
                    hit_at_k(ranked, relevant, k),
                    len(relevant),
                )
            )
        pairs.extend(q_pairs)
        scores.append(
            QuestionScore(
                question_id=q.id,
                kind=q.kind,
                recall=fmean(p.recall for p in q_pairs) if q_pairs else None,
                hit_rate=fmean(1.0 if p.hit else 0.0 for p in q_pairs) if q_pairs else None,
                missed=[p.candidate_id for p in q_pairs if not p.hit],
                uncovered=uncovered,
            )
        )
    return MethodReport(k=k, questions=scores, pairs=pairs)
