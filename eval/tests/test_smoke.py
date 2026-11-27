"""Format du jeu de fumée et cohérence avec un corpus jouet ; le vrai fichier se charge."""

from __future__ import annotations

from typing import Any

import pytest

from moi_electeur_eval.smoke import corpus_issues, load_questions, pages_label, parse_question


def raw(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "q1",
        "question": "Que proposent les candidats sur X ?",
        "kind": "theme",
        "theme": "social",
        "expected": {"alice": [{"chunk_id": "aaa-0001", "document_title": "Doc", "pages": "2-3"}]},
        "silent": [],
        "note": "",
    }
    return {**base, **over}


def test_question_valide() -> None:
    q = parse_question(raw())
    assert q.relevant("alice") == {"aaa-0001"}
    assert q.relevant("bruno") == set()


@pytest.mark.parametrize(
    "over",
    [
        {"kind": "inconnu"},
        {"kind": "recommandation"},  # avec attendus
        {"expected": {}},  # thème sans attendu
        {"kind": "silence"},  # piège sans silencieux
        {"silent": ["bruno"]},  # silencieux hors piège
        {"kind": "silence", "silent": ["alice"]},  # attendu et silencieux
        {"expected": {"alice": []}},
    ],
)
def test_questions_invalides(over: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        parse_question(raw(**over))


def test_recommandation_sans_attendu() -> None:
    q = parse_question(raw(kind="recommandation", expected={}, theme=None))
    assert q.expected == {} and q.silent == []


def test_corpus_issues() -> None:
    q = parse_question(raw(kind="silence", silent=["bruno"]))
    chunks = [
        {
            "id": "aaa-0001",
            "candidate_id": "alice",
            "document_title": "Doc",
            "page_number": 2,
            "page_end": 3,
        },
        {
            "id": "bbb-0001",
            "candidate_id": "bruno",
            "document_title": "Doc",
            "page_number": 1,
            "page_end": 1,
        },
    ]
    assert corpus_issues([q], chunks) == []
    moved = [{**chunks[0], "page_end": 4}, chunks[1]]
    assert any("pages 2-3 au lieu de 2-4" in i for i in corpus_issues([q], moved))
    assert any("extrait inconnu" in i for i in corpus_issues([q], chunks[1:]))
    other = [{**chunks[0], "candidate_id": "bruno"}, chunks[1]]
    assert any("appartient à bruno" in i for i in corpus_issues([q], other))
    assert any("candidat inconnu bruno" in i for i in corpus_issues([q], chunks[:1]))


def test_pages_label() -> None:
    assert pages_label(3, 3) == "3"
    assert pages_label(3, 4) == "3-4"


def test_jeu_2022_conforme_au_plan() -> None:
    questions = load_questions()
    kinds = [q.kind for q in questions]
    assert 13 <= len(questions) <= 20
    assert kinds.count("silence") == 3
    assert kinds.count("recommandation") == 2
    for q in questions:
        assert all(c.islower() for c in q.id if c.isalpha())
