"""Tests de `pipeline validate` : la démo passe, chaque règle rejette un cas cassé."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from moi_electeur_pipeline.paths import elections_dir
from moi_electeur_pipeline.validate import validate_election

Docs = dict[str, Any]


def messages(path: Path) -> str:
    return "\n".join(map(str, validate_election(path)))


def test_demo_commitee_valide() -> None:
    assert validate_election(elections_dir() / "demo-fictive") == []


def test_demo_generee_valide(demo_docs: Docs, write_election: Callable[[Docs], Path]) -> None:
    assert validate_election(write_election(demo_docs)) == []


def _mutate_candidate_xy(d: Docs) -> None:
    d["election_config.json"]["candidates"][0]["x"] = 3.0


def _mutate_position_xy(d: Docs) -> None:
    d["positions.json"]["positions"][0]["y"] = 1


def _mutate_review_without_reviewer(d: Docs) -> None:
    d["positions.json"]["positions"][0]["review"] = {"status": "validated"}


def _mutate_value_out_of_range(d: Docs) -> None:
    d["positions.json"]["positions"][0]["value"] = 3


def _mutate_too_few_statements(d: Docs) -> None:
    d["statements.json"]["statements"] = d["statements.json"]["statements"][:20]


def _mutate_unknown_theme(d: Docs) -> None:
    d["statements.json"]["statements"][0]["theme"] = "inconnu"


def _mutate_theme_coverage(d: Docs) -> None:
    for s in d["statements.json"]["statements"]:
        if s["theme"] == "institutions":
            s["theme"] = "economie"


def _mutate_same_direction(d: Docs) -> None:
    for s in d["statements.json"]["statements"]:
        if s["axis"] == "x":
            s["direction"] = 1


def _mutate_axis_coverage(d: Docs) -> None:
    for s in d["statements.json"]["statements"]:
        if s["axis"] == "x" and s["id"] != "s01" and s["id"] != "s02":
            s["axis"] = "y"


def _mutate_duplicate_position(d: Docs) -> None:
    d["positions.json"]["positions"].append(dict(d["positions.json"]["positions"][0]))


def _mutate_missing_position(d: Docs) -> None:
    d["positions.json"]["positions"].pop()


def _mutate_unknown_candidate(d: Docs) -> None:
    d["positions.json"]["positions"][0]["candidate_id"] = "c99"


def _mutate_no_evidence(d: Docs) -> None:
    p = next(p for p in d["positions.json"]["positions"] if p["value"] is not None)
    p["evidence"] = []


def _mutate_revealing_alias(d: Docs) -> None:
    c = d["election_config.json"]["candidates"][0]
    c["blind_alias"] = f"Alias de {c['name']}"


def _mutate_duplicate_alias(d: Docs) -> None:
    cands = d["election_config.json"]["candidates"]
    cands[1]["blind_alias"] = cands[0]["blind_alias"]


def _mutate_election_id(d: Docs) -> None:
    d["statements.json"]["election_id"] = "autre"


def _mutate_bad_date(d: Docs) -> None:
    d["election_config.json"]["date_first_round"] = "2027-13-45"


def _mutate_unknown_statement(d: Docs) -> None:
    d["positions.json"]["positions"][0]["statement_id"] = "s99"


def _mutate_corpus_unknown_candidate(d: Docs) -> None:
    d["election_config.json"]["corpus"].append(
        {
            "candidate_id": "c99",
            "document_title": "Programme",
            "type": "pdf",
            "source_url": "https://example.org/p.pdf",
            "local_path": "sources/c99/p.pdf",
            "sha256": "0" * 64,
            "retrieved_at": "2026-11-17",
        }
    )


def _mutate_measure_unknown_candidate(d: Docs) -> None:
    d["measures.json"]["measures"][0]["candidate_id"] = "c99"


def _mutate_measure_unknown_theme(d: Docs) -> None:
    d["measures.json"]["measures"][0]["theme"] = "inconnu"


def _mutate_measure_duplicate(d: Docs) -> None:
    ms = d["measures.json"]["measures"]
    ms[1]["id"] = ms[0]["id"]


def _mutate_measure_no_evidence(d: Docs) -> None:
    d["measures.json"]["measures"][0]["evidence"] = []


def _mutate_duplicate_theme(d: Docs) -> None:
    themes = d["election_config.json"]["themes"]
    themes.append(dict(themes[0]))


def _mutate_duplicate_candidate(d: Docs) -> None:
    cands = d["election_config.json"]["candidates"]
    cands[1]["id"] = cands[0]["id"]


def _mutate_corrected_no_evidence(d: Docs) -> None:
    p = next(p for p in d["positions.json"]["positions"] if p["value"] is not None)
    p["review"]["status"] = "corrected"
    p["evidence"] = []


def _mutate_alias_surname(d: Docs) -> None:
    c = d["election_config.json"]["candidates"][0]
    c["blind_alias"] = "Candidat·e " + c["name"].split()[-1]


def _mutate_evidence_outside_corpus(d: Docs) -> None:
    d["election_config.json"]["fictional"] = False


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_mutate_candidate_xy, "Additional properties"),
        (_mutate_position_xy, "Additional properties"),
        (_mutate_review_without_reviewer, "reviewer"),
        (_mutate_value_out_of_range, "maximum"),
        (_mutate_too_few_statements, "too short"),
        (_mutate_unknown_theme, "thème inconnu"),
        (_mutate_theme_coverage, "thème institutions"),
        (_mutate_same_direction, "sens non alternés"),
        (_mutate_axis_coverage, "axe x"),
        (_mutate_duplicate_position, "2 positions pour le même couple"),
        (_mutate_missing_position, "position manquante"),
        (_mutate_unknown_candidate, "candidat inconnu"),
        (_mutate_no_evidence, "sans citation"),
        (_mutate_revealing_alias, "révèle"),
        (_mutate_duplicate_alias, "alias aveugle en double"),
        (_mutate_election_id, "election_id"),
        (_mutate_bad_date, "is not a 'date'"),
        (_mutate_unknown_statement, "affirmation inconnue"),
        (_mutate_corpus_unknown_candidate, "corpus : candidat inconnu"),
        (_mutate_measure_unknown_candidate, "m001 : candidat inconnu"),
        (_mutate_measure_unknown_theme, "m001 : thème inconnu"),
        (_mutate_measure_duplicate, "mesure en double"),
        (_mutate_measure_no_evidence, "mesure retenue sans citation"),
        (_mutate_duplicate_theme, "thème en double"),
        (_mutate_duplicate_candidate, "candidat en double"),
        (_mutate_corrected_no_evidence, "sans citation"),
        (_mutate_alias_surname, "révèle"),
        (_mutate_evidence_outside_corpus, "document cité hors corpus"),
    ],
)
def test_regle_rejette_cas_casse(
    demo_docs: Docs,
    write_election: Callable[[Docs], Path],
    mutate: Callable[[Docs], None],
    expected: str,
) -> None:
    mutate(demo_docs)
    assert expected in messages(write_election(demo_docs))


def test_fichier_manquant(demo_docs: Docs, write_election: Callable[[Docs], Path]) -> None:
    del demo_docs["positions.json"]
    assert "fichier manquant" in messages(write_election(demo_docs))


def test_measures_facultatif(demo_docs: Docs, write_election: Callable[[Docs], Path]) -> None:
    del demo_docs["measures.json"]
    assert validate_election(write_election(demo_docs)) == []


def test_json_invalide(demo_docs: Docs, write_election: Callable[[Docs], Path]) -> None:
    path = write_election(demo_docs)
    (path / "statements.json").write_text("{pas du json", encoding="utf-8")
    assert "JSON invalide" in messages(path)


def test_dossier_et_id_differents(demo_docs: Docs, write_election: Callable[..., Path]) -> None:
    assert "différent du dossier" in messages(write_election(demo_docs, "autre-nom"))


def test_silence_valide_sans_citation(
    demo_docs: Docs, write_election: Callable[[Docs], Path]
) -> None:
    p = next(p for p in demo_docs["positions.json"]["positions"] if p["value"] is None)
    assert p["review"]["status"] == "validated" and p["evidence"] == []
    assert validate_election(write_election(demo_docs)) == []
