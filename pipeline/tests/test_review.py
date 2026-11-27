"""Revue humaine des propositions (PLAN § 5.3, D30, D31) : file, décisions, écriture validée.

Mêmes données que `test_propose.py` (démo fictive, extraits simulés), propositions faites par
le client simulé puis écrites au statut `pending`.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from test_propose import (
    _all_measures,
    _all_positions,
    _chunks,
    _position,
    _position_items,
    _read,
    _record,
    _write_positions,
    measure_reply,
)

from moi_electeur_pipeline.propose import (
    append_record,
    load_records,
    proposals_path,
    write_measures,
)
from moi_electeur_pipeline.review import (
    ReviewError,
    default_reviewer,
    highlight,
    measure_queue,
    pdf_link,
    position_queue,
    progress,
    review_measure,
    review_position,
)
from moi_electeur_pipeline.validate import compass_ready, validate_election

# Fixtures `election` et `cli` de test_propose.py.
pytest_plugins = ["test_propose"]

DAY = date(2026, 11, 29)


@pytest.fixture
def proposed(election: Path) -> Path:
    records = _all_positions(election)
    item = _position_items(election, candidates=["c2"])[3]
    flagged = _record(item, _position(1, [{"extrait": 1, "text": item.chunks[0]["text"]}], "low"))
    append_record(proposals_path(election, "position"), flagged)
    records[flagged["custom_id"]] = flagged
    _write_positions(election, records)
    measures = _all_measures(election, measure_reply)
    write_measures(election, _read(election, "election_config.json"), measures)
    return election


def _position_of(election: Path, cand: str, stmt: str) -> dict[str, Any]:
    positions = _read(election, "positions.json")["positions"]
    return next(p for p in positions if (p["candidate_id"], p["statement_id"]) == (cand, stmt))


# File de revue.


def test_file_des_positions_signalements_d_abord(proposed: Path) -> None:
    queue = position_queue(proposed)
    assert len(queue) == 180
    first = queue[0]
    assert (first["candidate_id"], first["statement_id"]) == ("c2", "s04")
    assert "confiance_faible" in first["reasons"]
    rest = queue[1:]
    assert [(e["candidate_id"], e["statement_id"]) for e in rest[:2]] == [
        ("c1", "s01"),
        ("c2", "s01"),
    ]


def test_file_sans_les_positions_revues(proposed: Path) -> None:
    review_position(proposed, "c1", "s01", decision="validated", reviewer="r", on=DAY)
    queue = position_queue(proposed)
    assert len(queue) == 179 and ("c1", "s01") not in {
        (e["candidate_id"], e["statement_id"]) for e in queue
    }
    assert len(position_queue(proposed, include_reviewed=True)) == 180


def test_file_des_mesures_chiffrages_d_abord(proposed: Path) -> None:
    queue = measure_queue(proposed)
    assert len(queue) == 36
    assert queue[0]["reasons"] == ["chiffrage à vérifier"]


# Décisions sur les positions.


def test_validation_tracee(proposed: Path) -> None:
    review_position(
        proposed, "c1", "s01", decision="validated", reviewer="r", on=DAY, note="Conforme."
    )
    p = _position_of(proposed, "c1", "s01")
    assert p["review"] == {
        "status": "validated",
        "reviewer": "r",
        "date": "2026-11-29",
        "note": "Conforme.",
    }
    assert p["value"] == 1 and "proposed_value" not in p
    assert validate_election(proposed) == []


def test_correction_garde_la_valeur_proposee(proposed: Path) -> None:
    review_position(
        proposed,
        "c1",
        "s01",
        decision="corrected",
        reviewer="r",
        on=DAY,
        value=2,
        confidence="high",
    )
    p = _position_of(proposed, "c1", "s01")
    assert (p["value"], p["proposed_value"], p["confidence"]) == (2, 1, "high")
    assert p["review"]["status"] == "corrected"
    # Seconde correction : la valeur proposée d'origine est conservée.
    review_position(proposed, "c1", "s01", decision="corrected", reviewer="r", on=DAY, value=-1)
    p = _position_of(proposed, "c1", "s01")
    assert (p["value"], p["proposed_value"]) == (-1, 1)
    # Retour à la validation : valeur d'origine rétablie, plus de valeur proposée.
    review_position(proposed, "c1", "s01", decision="validated", reviewer="r", on=DAY)
    p = _position_of(proposed, "c1", "s01")
    assert p["value"] == 1 and "proposed_value" not in p
    assert validate_election(proposed) == []


def test_correction_en_silence_sans_citation(proposed: Path) -> None:
    review_position(proposed, "c1", "s01", decision="corrected", reviewer="r", on=DAY, value=None)
    p = _position_of(proposed, "c1", "s01")
    assert (p["value"], p["evidence"], p["proposed_value"]) == (None, [], 1)


def test_correction_avec_nouvelle_citation(proposed: Path) -> None:
    text = "L'âge de départ sera ramené  à 60 ans."
    review_position(
        proposed, "c1", "s06", decision="corrected", reviewer="r", on=DAY, value=2, quotes=[text]
    )
    p = _position_of(proposed, "c1", "s06")
    chunk = _chunks("c1")[1]
    assert p["evidence"] == [
        {
            "quote": "L’âge de départ sera ramené à 60 ans.",
            "document_title": chunk["document_title"],
            "page": chunk["page_number"],
            "chunk_id": chunk["id"],
        }
    ]


def test_citation_introuvable_refusee(proposed: Path) -> None:
    before = (proposed / "positions.json").read_text(encoding="utf-8")
    with pytest.raises(ReviewError, match="introuvable"):
        review_position(
            proposed,
            "c1",
            "s06",
            decision="corrected",
            reviewer="r",
            on=DAY,
            value=2,
            quotes=["Une phrase absente de tous les extraits du candidat."],
        )
    assert (proposed / "positions.json").read_text(encoding="utf-8") == before


def test_citation_d_un_autre_candidat_refusee(proposed: Path) -> None:
    lookup = proposed / "sources" / "chunks.jsonl"
    other = {
        **_chunks("c2")[2],
        "id": "c2-unique-0009",
        "text": "Phrase propre au seul candidat c2 ici.",
    }
    lookup.write_text(
        lookup.read_text(encoding="utf-8") + json.dumps(other) + "\n", encoding="utf-8"
    )
    with pytest.raises(ReviewError, match="introuvable"):
        review_position(
            proposed,
            "c1",
            "s11",
            decision="corrected",
            reviewer="r",
            on=DAY,
            value=2,
            quotes=[other["text"]],
        )
    review_position(
        proposed,
        "c2",
        "s11",
        decision="corrected",
        reviewer="r",
        on=DAY,
        value=2,
        quotes=[other["text"]],
    )


def test_valeur_sans_citation_refusee(proposed: Path) -> None:
    review_position(proposed, "c1", "s01", decision="corrected", reviewer="r", on=DAY, value=None)
    before = (proposed / "positions.json").read_text(encoding="utf-8")
    with pytest.raises(ReviewError, match="sans citation"):
        review_position(proposed, "c1", "s01", decision="corrected", reviewer="r", on=DAY, value=2)
    assert (proposed / "positions.json").read_text(encoding="utf-8") == before


def test_rejet_et_reviseur_obligatoire(proposed: Path) -> None:
    review_position(
        proposed, "c1", "s01", decision="rejected", reviewer="r", on=DAY, note="Hors sujet."
    )
    assert _position_of(proposed, "c1", "s01")["review"]["status"] == "rejected"
    with pytest.raises(ReviewError, match="réviseur"):
        review_position(proposed, "c1", "s02", decision="validated", reviewer=" ", on=DAY)
    with pytest.raises(ReviewError, match="décision"):
        review_position(proposed, "c1", "s02", decision="pending", reviewer="r", on=DAY)
    with pytest.raises(ReviewError, match="inconnue"):
        review_position(proposed, "c9", "s02", decision="validated", reviewer="r", on=DAY)


def test_tout_revu_rend_la_boussole_publiable(proposed: Path) -> None:
    for e in position_queue(proposed):
        review_position(
            proposed,
            e["candidate_id"],
            e["statement_id"],
            decision="validated",
            reviewer="r",
            on=DAY,
        )
    for e in measure_queue(proposed):  # mesures revues aussi (relecture de fin de M3)
        review_measure(proposed, e["id"], decision="validated", reviewer="r", on=DAY)
    assert compass_ready(proposed)
    assert progress(proposed)["positions"] == {"validated": 180}


# Décisions sur les mesures.


def test_mesure_corrigee_garde_la_proposition(proposed: Path) -> None:
    costing = {
        "status": "partiel",
        "amount_eur": None,
        "period": None,
        "quote": "Coût : 10 milliards d'euros par an.",
    }
    review_measure(
        proposed,
        "m001",
        decision="corrected",
        reviewer="r",
        on=DAY,
        title="Retraite à 60 ans",
        costing=costing,
    )
    m = next(m for m in _read(proposed, "measures.json")["measures"] if m["id"] == "m001")
    assert m["title"] == "Retraite à 60 ans" and m["costing"] == costing
    assert m["proposed"]["title"] == "Ramener l'âge de départ à 60 ans"
    assert m["proposed"]["costing"]["status"] == "chiffre"
    assert "summary" not in m["proposed"]  # champ inchangé
    assert validate_election(proposed) == []
    review_measure(proposed, "m001", decision="validated", reviewer="r", on=DAY)
    m = next(m for m in _read(proposed, "measures.json")["measures"] if m["id"] == "m001")
    assert m["title"] == "Ramener l'âge de départ à 60 ans" and "proposed" not in m
    assert m["costing"]["status"] == "chiffre"


def test_mesure_rejetee(proposed: Path) -> None:
    review_measure(proposed, "m002", decision="rejected", reviewer="r", on=DAY, note="Doublon.")
    assert progress(proposed)["measures"] == {"pending": 35, "rejected": 1}
    with pytest.raises(ReviewError, match="inconnue"):
        review_measure(proposed, "m999", decision="validated", reviewer="r", on=DAY)


# Affichage.


def test_surlignage_echappe_le_html() -> None:
    html = highlight(
        "Avant <b>gras</b>. L’âge de départ sera ramené à 60 ans. Après.",
        ["L'âge de départ sera ramené à 60 ans."],
    )
    assert "&lt;b&gt;" in html
    assert "<mark>L’âge de départ sera ramené à 60 ans.</mark>" in html
    assert highlight("Rien à voir.", ["Citation absente du texte."]) == "Rien à voir."


def test_lien_vers_la_page() -> None:
    chunk = _chunks("c1")[1]
    assert pdf_link(chunk) == "https://example.org/c1.pdf#page=2"
    assert pdf_link({**chunk, "source_url": "javascript:alert(1)"}) is None


def test_reviseur_par_defaut(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOI_ELECTEUR_REVIEWER", raising=False)
    assert default_reviewer() == "mainteneur"
    monkeypatch.setenv("MOI_ELECTEUR_REVIEWER", "relecteur-2")
    assert default_reviewer() == "relecteur-2"


def test_commande_review_affiche_l_avancement(proposed: Path) -> None:
    from typer.testing import CliRunner

    from moi_electeur_pipeline.cli import app

    review_position(proposed, "c1", "s01", decision="validated", reviewer="r", on=DAY)
    result = CliRunner().invoke(app, ["review", str(proposed)])
    assert result.exit_code == 0, result.output
    assert "positions : 1/180 revues" in result.output
    assert "mesures : 0/36 revues" in result.output
    assert "review/review_positions.py" in result.output


def test_propositions_intactes(proposed: Path) -> None:
    before = load_records(proposals_path(proposed, "position"))
    review_position(proposed, "c1", "s01", decision="corrected", reviewer="r", on=DAY, value=2)
    assert load_records(proposals_path(proposed, "position")) == before
    assert json.loads((proposed / "positions.json").read_text(encoding="utf-8"))


# Suites de la relecture de fin de M3.


def _validate_all(election: Path) -> None:
    for e in position_queue(election):
        review_position(
            election,
            e["candidate_id"],
            e["statement_id"],
            decision="validated",
            reviewer="r",
            on=DAY,
        )


def test_boussole_non_publiable_tant_que_des_mesures_attendent(proposed: Path) -> None:
    _validate_all(proposed)
    assert not compass_ready(proposed)  # 36 mesures encore en attente
    for e in measure_queue(proposed):
        review_measure(proposed, e["id"], decision="validated", reviewer="r", on=DAY)
    assert compass_ready(proposed)


def test_build_retire_les_fichiers_d_une_boussole_redevenue_non_prete(
    proposed: Path, tmp_path: Path
) -> None:
    from moi_electeur_pipeline.build import build_election

    _validate_all(proposed)
    for e in measure_queue(proposed):
        review_measure(proposed, e["id"], decision="validated", reviewer="r", on=DAY)
    target = build_election(proposed, tmp_path / "out")
    assert (target / "positions.json").is_file()
    doc = _read(proposed, "positions.json")
    doc["positions"][0]["review"] = {"status": "pending"}
    (proposed / "positions.json").write_text(json.dumps(doc), encoding="utf-8")
    build_election(proposed, tmp_path / "out")
    assert sorted(f.name for f in target.iterdir()) == ["election_config.json"]


def test_decision_sans_sources_locales(proposed: Path) -> None:
    (proposed / "sources" / "chunks.jsonl").unlink()
    review_position(proposed, "c1", "s01", decision="rejected", reviewer="r", on=DAY)
    review_position(proposed, "c1", "s02", decision="validated", reviewer="r", on=DAY)
    with pytest.raises(ReviewError, match="sources"):
        review_position(
            proposed,
            "c1",
            "s03",
            decision="corrected",
            reviewer="r",
            on=DAY,
            value=2,
            quotes=["Une citation quelconque du programme."],
        )


def test_citations_refusees_pour_un_silence(proposed: Path) -> None:
    with pytest.raises(ReviewError, match="silence"):
        review_position(
            proposed,
            "c1",
            "s01",
            decision="corrected",
            reviewer="r",
            on=DAY,
            value=None,
            quotes=["L'âge de départ sera ramené à 60 ans."],
        )


def test_chiffrage_inchange_ni_reecrit_ni_reverifie(proposed: Path) -> None:
    m = next(x for x in _read(proposed, "measures.json")["measures"] if x["id"] == "m001")
    (proposed / "sources" / "chunks.jsonl").unlink()  # aucune revérification possible
    review_measure(
        proposed,
        "m001",
        decision="corrected",
        reviewer="r",
        on=DAY,
        title="Nouveau titre",
        costing=dict(m["costing"]),
    )
    after = next(x for x in _read(proposed, "measures.json")["measures"] if x["id"] == "m001")
    assert after["costing"] == m["costing"]
    assert after["proposed"] == {"title": m["title"]}


def test_ecriture_restauree_si_la_validation_plante(
    proposed: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from moi_electeur_pipeline import review as review_module

    before = (proposed / "positions.json").read_text(encoding="utf-8")

    def boom(_: Path) -> list[Any]:
        raise RuntimeError("panne")

    monkeypatch.setattr(review_module, "validate_election", boom)
    with pytest.raises(RuntimeError):
        review_position(proposed, "c1", "s01", decision="validated", reviewer="r", on=DAY)
    assert (proposed / "positions.json").read_text(encoding="utf-8") == before
    assert not list(proposed.glob("*.tmp"))
