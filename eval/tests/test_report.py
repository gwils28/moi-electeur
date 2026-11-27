"""Fixture compacte (aller-retour) et tableaux de rappel à partir d'une fixture jouet."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from moi_electeur_eval.collect import filtered_tsquery, fuse
from moi_electeur_eval.report import (
    decode_fixture,
    encode_fixture,
    format_table,
    load_fixture,
    reports,
    write_fixture,
)
from moi_electeur_eval.smoke import ExpectedChunk, Question

QUESTIONS = [
    Question("q1", "?", "theme", None, {"A": [ExpectedChunk("a1", "D", "1")]}),
]


def fixture() -> dict[str, Any]:
    rankings = {"q1": {"A": ["a2", "a1"], "B": ["b1"]}}
    return {
        "election_id": "test",
        "models": {
            "m": {
                "candidates": ["A", "B"],
                "keep": 6,
                "rankings": {"semantique": rankings, "rrf": {"q1": {"A": ["a3"], "B": []}}},
            }
        },
    }


def test_aller_retour(tmp_path: Path) -> None:
    f = fixture()
    enc = encode_fixture(f)
    assert enc["chunk_ids"] == ["a1", "a2", "a3", "b1"]
    assert enc["models"]["m"]["rankings"]["semantique"]["q1"]["A"] == [1, 0]
    assert decode_fixture(enc) == f
    write_fixture(tmp_path / "f.json", f)
    assert load_fixture(tmp_path / "f.json") == f


def test_reports_et_tableau() -> None:
    res = reports(fixture(), QUESTIONS, k=4)
    assert list(res) == [("m", "semantique"), ("m", "rrf")]
    assert res[("m", "semantique")].recall == 1.0
    assert res[("m", "rrf")].recall == 0.0
    assert not res[("m", "rrf")].full_coverage  # B sans extrait
    table = format_table(res)
    assert "| m | sémantique seul | 1.000 |" in table
    assert "| m | RRF (servi) | 0.000 |" in table


def test_fusion_rrf_calculee_a_la_main() -> None:
    # y : 1/62 + 1/61 ; x : 1/61 ; z : 1/62.
    assert fuse(["x", "y"], ["y", "z"]) == ["y", "x", "z"]
    # Égalité x / z départagée par identifiant.
    assert fuse(["z"], ["x"]) == ["x", "z"]


def test_requete_plein_texte_filtree() -> None:
    df = {"le": 0.99, "candidat": 0.05, "otan": 0.02}
    assert filtered_tsquery(["le", "candidat", "otan"], df) == "'candidat' | 'otan'"
    assert filtered_tsquery(["aujourd'hui"], {}) == "'aujourd''hui'"
    assert filtered_tsquery(["le"], df) == ""
