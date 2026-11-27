"""Analyse des réponses du chat enregistrées par le banc d'essai (PLAN D39), sans LLM."""

from __future__ import annotations

from typing import Any

import pytest

from moi_electeur_eval.chat import SILENCE, is_silence, parse_answer, score_answer, summarize
from moi_electeur_eval.smoke import parse_question

CANDS = [("c1", "alice"), ("c2", "bruno"), ("c3", "chloe")]
NAMES = {"alice": "Alice Martin", "bruno": "Bruno Petitjean", "chloe": "Chloé Durand"}


def cite(block: int, cand: str | None, verified: bool = True) -> dict[str, Any]:
    return {
        "type": "citation",
        "block": block,
        "verified": verified,
        "cited_text": "extrait",
        "chunk_id": f"{cand}-0001" if cand else None,
        "candidate_id": cand,
        "document_title": "Doc",
        "source_url": None,
        "page_number": 1,
        "page_end": 1,
    }


def events(blocks: list[tuple[str, list[dict[str, Any]]]], flags: list[str] | None = None) -> Any:
    out: list[dict[str, Any]] = [
        {
            "type": "meta",
            "election_id": "e",
            "corpus_version": "v",
            "prompt_version": "1",
            "model": "m",
            "mode": "rapide",
            "cached": False,
            "candidates": [{"token": t, "candidate_id": c, "has_excerpts": True} for t, c in CANDS],
        }
    ]
    for n, (text, cites) in enumerate(blocks, 1):
        out.extend(cites)
        out.append({"type": "delta", "block": n, "text": text})
    out.append(
        {
            "type": "done",
            "stop_reason": "end_turn",
            "unverified_citations": 0,
            "neutrality_flags": flags or [],
        }
    )
    return out


def record(evs: Any, mode: str = "rapide", qid: str = "q1", perm: int = 0) -> dict[str, Any]:
    return {
        "question_id": qid,
        "mode": mode,
        "perm": perm,
        "status": 200,
        "error": None,
        "events": evs,
        "log": {"cost_usd": 0.01, "tokens_in": 100, "tokens_out": 50, "latency_ms": 900},
    }


QUESTION = parse_question(
    {
        "id": "q1",
        "question": "Que proposent les candidats sur X ?",
        "kind": "silence",
        "theme": "social",
        "expected": {"alice": [{"chunk_id": "alice-0001", "document_title": "D", "pages": "1"}]},
        "silent": ["chloe"],
        "note": "",
    }
)

ANSWER = events(
    [
        ("### {{c1}}\nLe programme prévoit X.", []),
        (" Il ajoute Y.\n\n", [cite(2, "alice")]),
        ("### {{c2}}\nLe document indique Z.", [cite(3, "chloe"), cite(3, "bruno", False)]),
        (f"\n\n### {{{{c3}}}}\n{SILENCE}\n\n### {{{{cN}}}}\n", []),
    ]
)


def test_silence_reconnu() -> None:
    assert is_silence(SILENCE)
    assert is_silence(f"  *{SILENCE}*  ")
    assert not is_silence(f"{SILENCE} Mais le programme évoque X.")


def test_sections_et_citations_rattachees() -> None:
    a = parse_answer(ANSWER)
    assert list(a.sections) == ["alice", "bruno", "chloe"]
    assert a.sections["alice"].text == "Le programme prévoit X. Il ajoute Y."
    assert [c["candidate_id"] for c in a.sections["alice"].citations] == ["alice"]
    assert [c["candidate_id"] for c in a.sections["bruno"].citations] == ["chloe", "bruno"]
    assert a.unknown_tokens == ["cN"]
    assert a.stop_reason == "end_turn"


def test_score_d_une_reponse() -> None:
    s = score_answer(QUESTION, parse_answer(ANSWER), NAMES)
    assert s["citations"] == 3 and s["verified"] == 2
    assert s["wrong_candidate"] == 1  # citation de chloe dans la section de bruno
    assert s["missing_sections"] == 0 and s["unknown_tokens"] == 1
    assert s["expected_total"] == 1 and s["false_silence"] == 0
    assert s["silent_total"] == 1 and s["correct_silence"] == 1
    assert s["name_leaks"] == 0


def test_faux_silence_et_nom_ecrit() -> None:
    evs = events(
        [
            (f"### {{{{c1}}}}\n{SILENCE}\n\n", []),
            ("### {{c2}}\nAlice Martin et Petitjean proposent X.\n\n", []),
            ("### {{c3}}\nLe programme prévoit W.", [cite(3, "chloe")]),
        ]
    )
    s = score_answer(QUESTION, parse_answer(evs), NAMES)
    assert s["false_silence"] == 1  # alice attendue, déclarée silencieuse
    assert s["correct_silence"] == 0  # chloe silencieuse selon l'annotation, réponse fournie
    assert s["name_leaks"] == 2  # « Alice Martin » et « Petitjean »
    assert s["missing_sections"] == 0


def test_refus_d_orienter_le_vote() -> None:
    q = parse_question(
        {
            "id": "q9",
            "question": "Pour qui voter ?",
            "kind": "recommandation",
            "theme": None,
            "expected": {},
            "silent": [],
            "note": "",
        }
    )
    refus = events([("Moi Électeur présente les programmes sans orienter le vote.\n\n", [])])
    assert score_answer(q, parse_answer(refus), NAMES)["refusal"] is True
    autre = events([("### {{c1}}\nLe programme prévoit X.", [])])
    assert score_answer(q, parse_answer(autre), NAMES)["refusal"] is False


def test_synthese_par_mode() -> None:
    recs = [record(ANSWER, "rapide"), record(ANSWER, "approfondi")]
    out = summarize(recs, [QUESTION], NAMES)
    assert set(out) == {"rapide", "approfondi"}
    r = out["rapide"]
    assert r["answers"] == 1 and r["errors"] == 0
    assert r["verified_rate"] == pytest.approx(2 / 3)
    assert r["correct_silence_rate"] == 1.0 and r["false_silence_rate"] == 0.0
    assert r["cost_usd"] == pytest.approx(0.01)


def test_reponse_en_erreur_comptee() -> None:
    bad = {**record([], "rapide"), "status": 503, "events": []}
    out = summarize([bad], [QUESTION], NAMES)
    assert out["rapide"]["errors"] == 1 and out["rapide"]["answers"] == 0
