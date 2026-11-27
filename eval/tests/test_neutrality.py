"""Neutralité par permutation (PLAN D41) : effet du rang de présentation sur les sections."""

from __future__ import annotations

from typing import Any

import pytest
from test_chat import CANDS, record

from moi_electeur_eval.neutrality import permutation_effects


def answer(order: list[str], lengths: dict[str, int], cites: dict[str, int]) -> Any:
    tokens = {c: f"c{i}" for i, c in enumerate(order, 1)}
    evs: list[dict[str, Any]] = [
        {
            "type": "meta",
            "election_id": "e",
            "corpus_version": "v",
            "prompt_version": "1",
            "model": "m",
            "mode": "rapide",
            "cached": False,
            "candidates": [
                {"token": tokens[c], "candidate_id": c, "has_excerpts": True} for c in order
            ],
        }
    ]
    for n, c in enumerate(order, 1):
        evs += [
            {
                "type": "citation",
                "block": n,
                "verified": True,
                "cited_text": "x",
                "chunk_id": None,
                "candidate_id": c,
                "document_title": None,
                "source_url": None,
                "page_number": None,
                "page_end": None,
            }
            for _ in range(cites[c])
        ]
        evs.append(
            {
                "type": "delta",
                "block": n,
                "text": f"### {{{{{tokens[c]}}}}}\n" + "x" * lengths[c] + "\n\n",
            }
        )
    evs.append(
        {
            "type": "done",
            "stop_reason": "end_turn",
            "unverified_citations": 0,
            "neutrality_flags": [],
        }
    )
    return evs


IDS = [c for _, c in CANDS]


def test_aucun_effet_de_rang_quand_les_sections_suivent_le_candidat() -> None:
    lengths = {"alice": 300, "bruno": 200, "chloe": 100}
    cites = {"alice": 3, "bruno": 2, "chloe": 1}
    orders = [IDS, IDS[::-1], [IDS[1], IDS[2], IDS[0]]]
    recs = [record(answer(o, lengths, cites), perm=p) for p, o in enumerate(orders)]
    out = permutation_effects(recs)
    assert out["answers"] == 3 and out["questions"] == 1
    assert out["per_candidate_cv"]["alice"] == pytest.approx(0.0)
    assert out["by_rank"][1]["length"] == pytest.approx(200.0)  # moyenne des premiers
    assert abs(out["spearman_rank_length"]) < 0.6


def test_effet_de_rang_detecte() -> None:
    orders = [IDS, IDS[::-1], [IDS[1], IDS[2], IDS[0]]]
    recs = []
    for p, o in enumerate(orders):
        lengths = {c: 300 - 100 * i for i, c in enumerate(o)}  # le premier présenté écrit plus
        recs.append(record(answer(o, lengths, {c: 1 for c in o}), perm=p))
    out = permutation_effects(recs)
    assert out["spearman_rank_length"] == pytest.approx(-1.0)
    assert out["per_candidate_cv"]["alice"] > 0.3
