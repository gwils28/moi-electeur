"""Rappel@k et succès@k sur des classements jouets calculés à la main."""

from __future__ import annotations

import math

import pytest

from moi_electeur_eval.recall import evaluate, hit_at_k, recall_at_k
from moi_electeur_eval.smoke import ExpectedChunk, Question

RANKED = ["a", "b", "c", "d", "e"]


def test_rappel_normalise_par_min_k_et_pertinents() -> None:
    # Pertinents {b, e, x} : à k = 4 seul b est trouvé, sur min(4, 3) = 3 possibles.
    assert recall_at_k(RANKED, {"b", "e", "x"}, 4) == pytest.approx(1 / 3)
    assert recall_at_k(RANKED, {"b", "e", "x"}, 5) == pytest.approx(2 / 3)
    # Un seul pertinent trouvé : rappel 1, même si 3 places restent prises par d'autres.
    assert recall_at_k(RANKED, {"a"}, 4) == 1.0
    # Plus de pertinents que de places : 4 sur 4 vaut 1.
    assert recall_at_k(RANKED, set("abcdef"), 4) == 1.0
    assert recall_at_k(RANKED, set("abcdef"), 2) == 1.0
    assert recall_at_k([], {"a"}, 4) == 0.0


def test_succes_au_moins_un_pertinent() -> None:
    assert not hit_at_k(RANKED, {"b"}, 1)
    assert hit_at_k(RANKED, {"b"}, 2)
    assert not hit_at_k([], {"b"}, 4)


def test_arguments_invalides() -> None:
    with pytest.raises(ValueError):
        recall_at_k(RANKED, set(), 4)
    with pytest.raises(ValueError):
        recall_at_k(RANKED, {"a"}, 0)
    with pytest.raises(ValueError):
        hit_at_k(RANKED, {"a"}, 0)


def _q(qid: str, kind: str, expected: dict[str, list[str]], silent: list[str] = ()) -> Question:  # type: ignore[assignment]
    return Question(
        id=qid,
        question=f"question {qid}",
        kind=kind,
        theme=None,
        expected={c: [ExpectedChunk(i, "Doc", "1") for i in ids] for c, ids in expected.items()},
        silent=list(silent),
    )


def test_evaluate_jeu_jouet() -> None:
    questions = [
        _q("q1", "theme", {"A": ["a1", "a2"], "B": ["b1"]}),
        _q("q2", "silence", {"A": ["a9"]}, ["C"]),
        _q("q3", "recommandation", {}),
    ]
    rankings = {
        # A : a1 au rang 2 (1 sur 2) ; B : b1 au rang 5, hors des 4 premiers ; C : rien.
        "q1": {"A": ["a3", "a1", "a4", "a5"], "B": ["b2", "b3", "b4", "b5", "b1"], "C": []},
        "q2": {"A": ["a9"], "B": ["b1"], "C": ["c1"]},
        "q3": {"A": ["a1"], "B": ["b1"], "C": ["c1"]},
    }
    r = evaluate(questions, rankings, ["A", "B", "C"], k=4)
    q1, q2, q3 = r.questions
    assert q1.recall == pytest.approx(0.25)  # (1/2 + 0) / 2
    assert q1.hit_rate == pytest.approx(0.5)
    assert q1.missed == ["B"]
    assert q1.uncovered == ["C"]
    assert q2.recall == 1.0 and q2.uncovered == []
    assert q3.recall is None and q3.hit_rate is None and q3.missed == []
    assert r.recall == pytest.approx(0.625)  # macro : (0.25 + 1) / 2, q3 exclue
    assert r.recall_micro == pytest.approx(0.5)  # couples : 1/2, 0, 1
    assert r.hit_rate == pytest.approx(2 / 3)
    assert not r.full_coverage
    # À k = 5, b1 est trouvé.
    r5 = evaluate(questions, rankings, ["A", "B", "C"], k=5)
    assert r5.questions[0].recall == pytest.approx(0.75)


def test_evaluate_question_absente_des_classements() -> None:
    r = evaluate([_q("q1", "theme", {"A": ["a1"]})], {}, ["A"], k=4)
    assert r.questions[0].recall == 0.0
    assert r.questions[0].uncovered == ["A"]


def test_rapport_vide() -> None:
    r = evaluate([], {}, ["A"], k=4)
    assert math.isnan(r.recall) and math.isnan(r.hit_rate)
    assert r.full_coverage
