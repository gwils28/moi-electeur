"""Juge LLM des réponses du chat (PLAN D40) : requêtes, lecture des verdicts, synthèse."""

from __future__ import annotations

import json
from typing import Any

from test_chat import ANSWER, record

from moi_electeur_eval.judge import (
    JUDGE_MODEL,
    judge_requests,
    parse_judgement,
    summarize_judgements,
)


def test_requete_par_reponse_avec_passages_cites() -> None:
    reqs = judge_requests([record(ANSWER, "rapide"), record(ANSWER, "approfondi")])
    assert [r["custom_id"] for r in reqs] == ["j-q1-rapide", "j-q1-approfondi"]
    params = reqs[0]["params"]
    assert params["model"] == JUDGE_MODEL
    assert params["output_config"]["format"]["type"] == "json_schema"
    content = params["messages"][0]["content"]
    assert '<section jeton="c1">' in content and "Le programme prévoit X. Il ajoute Y." in content
    assert "<passage>extrait</passage>" in content
    assert "cN" not in content  # section au jeton inconnu ignorée


def test_requetes_ignorees_pour_les_erreurs_et_les_permutations() -> None:
    bad = {**record(ANSWER), "status": 503}
    perm = record(ANSWER, perm=1)
    assert judge_requests([bad, perm]) == []


def message(out: Any, stop: str = "end_turn") -> dict[str, Any]:
    return {
        "stop_reason": stop,
        "content": [{"type": "text", "text": json.dumps(out)}],
        "usage": {"input_tokens": 1000, "output_tokens": 200},
    }


VERDICT = {
    "sections": [
        {"token": "c1", "claims": 2, "unsupported": 1, "examples": ["Il ajoute Y."]},
        {"token": "c2", "claims": 1, "unsupported": 0, "examples": []},
        {"token": "c3", "claims": 0, "unsupported": 0, "examples": []},
    ]
}


def test_lecture_du_verdict() -> None:
    assert parse_judgement(message(VERDICT)) == VERDICT
    assert parse_judgement(message(VERDICT, stop="max_tokens")) is None
    assert parse_judgement(message({"sections": [{"token": "c1"}]})) is None


def test_synthese_par_mode() -> None:
    recs = [record(ANSWER, "rapide"), record(ANSWER, "approfondi")]
    verdicts = {"j-q1-rapide": VERDICT, "j-q1-approfondi": None}
    out = summarize_judgements(verdicts, recs)
    assert out["rapide"] == {
        "judged": 1,
        "failed": 0,
        "claims": 3,
        "unsupported": 1,
        "unsupported_rate": 1 / 3,
        "sections_with_unsupported": 1,
        "examples": [("q1", "alice", "Il ajoute Y.")],
    }
    assert out["approfondi"]["failed"] == 1 and out["approfondi"]["judged"] == 0
