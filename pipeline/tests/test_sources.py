"""`add-source` et `fetch` (PLAN D12, § 4.2) : réseau toujours simulé."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest
from helpers import make_pdf, read_config, write_corpus_election

from moi_electeur_pipeline.sources import SourceError, add_source, fetch_corpus
from moi_electeur_pipeline.validate import validate_election

URL = "https://web.archive.org/web/20220101000000id_/https://exemple.fr/programme.pdf"
URL2 = "https://web.archive.org/web/20220101000000id_/https://exemple.fr/profession-de-foi.pdf"
PDF = make_pdf([[("Programme", 20), ("Une mesure.", 11)]])
PDF2 = make_pdf([[("Profession de foi", 20), ("Un engagement.", 11)]])
TODAY = date(2026, 11, 19)


class FakeFetcher:
    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        return self.responses[url]


def _add(election: Path, fetcher: FakeFetcher, url: str = URL, title: str = "Programme") -> dict:
    return add_source(election, "c1", url, title, "pdf", fetcher=fetcher, today=TODAY)


def test_add_source_ecrit_une_entree_conforme(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    entry = _add(election, FakeFetcher({URL: PDF}))

    assert entry == {
        "candidate_id": "c1",
        "document_title": "Programme",
        "type": "pdf",
        "source_url": URL,
        "local_path": "sources/c1/programme.pdf",
        "sha256": hashlib.sha256(PDF).hexdigest(),
        "retrieved_at": "2026-11-19",
    }
    assert read_config(election)["corpus"] == [entry]
    assert (election / entry["local_path"]).read_bytes() == PDF
    assert validate_election(election) == []


def test_add_source_refuse_un_candidat_inconnu(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    with pytest.raises(SourceError, match="candidat inconnu"):
        add_source(election, "inconnu", URL, "Programme", "pdf", fetcher=FakeFetcher({URL: PDF}))


def test_add_source_refuse_une_url_en_double(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    fetcher = FakeFetcher({URL: PDF})
    _add(election, fetcher)
    with pytest.raises(SourceError, match="déjà"):
        _add(election, fetcher, title="Autre titre")
    assert len(read_config(election)["corpus"]) == 1


def test_add_source_refuse_un_document_identique_sous_une_autre_url(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    _add(election, FakeFetcher({URL: PDF}))
    with pytest.raises(SourceError, match="sha256"):
        _add(election, FakeFetcher({URL2: PDF}), url=URL2, title="Copie")


def test_add_source_refuse_un_pdf_qui_nen_est_pas_un(tmp_path: Path) -> None:
    """La Wayback renvoie parfois une page HTML d'erreur avec un code 200."""
    election = write_corpus_election(tmp_path)
    with pytest.raises(SourceError, match="PDF"):
        _add(election, FakeFetcher({URL: b"<html>Erreur</html>"}))
    assert read_config(election)["corpus"] == []
    assert not (election / "sources").exists()


def test_add_source_nomme_les_fichiers_sans_collision(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    other = "https://web.archive.org/web/2022id_/https://autre.fr/programme.pdf"
    _add(election, FakeFetcher({URL: PDF}))
    entry = _add(election, FakeFetcher({other: PDF2}), url=other, title="Programme bis")
    assert entry["local_path"] == "sources/c1/programme-2.pdf"


def test_fetch_ne_telecharge_pas_un_fichier_present_et_correct(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    _add(election, FakeFetcher({URL: PDF}))
    fetcher = FakeFetcher({})
    report = fetch_corpus(election, fetcher=fetcher)
    assert fetcher.calls == []
    assert report.present == ["sources/c1/programme.pdf"]
    assert report.downloaded == []


def test_fetch_telecharge_ce_qui_manque(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    entry = _add(election, FakeFetcher({URL: PDF}))
    (election / entry["local_path"]).unlink()
    report = fetch_corpus(election, fetcher=FakeFetcher({URL: PDF}))
    assert report.downloaded == [entry["local_path"]]
    assert (election / entry["local_path"]).read_bytes() == PDF


def test_fetch_echoue_si_le_document_distant_a_change(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    entry = _add(election, FakeFetcher({URL: PDF}))
    (election / entry["local_path"]).unlink()
    with pytest.raises(SourceError, match="sha256"):
        fetch_corpus(election, fetcher=FakeFetcher({URL: PDF2}))
    assert not (election / entry["local_path"]).exists()


def test_fetch_echoue_si_le_fichier_local_est_altere(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    entry = _add(election, FakeFetcher({URL: PDF}))
    (election / entry["local_path"]).write_bytes(PDF2)
    with pytest.raises(SourceError, match="altéré"):
        fetch_corpus(election, fetcher=FakeFetcher({URL: PDF}))


def test_add_source_refuse_un_type_inconnu_ou_une_url_non_http(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    fetcher = FakeFetcher({URL: PDF})
    with pytest.raises(SourceError, match="type inconnu"):
        add_source(election, "c1", URL, "Programme", "docx", fetcher=fetcher)
    with pytest.raises(SourceError, match="HTTP"):
        add_source(election, "c1", "file:///etc/passwd", "Programme", "pdf", fetcher=fetcher)
    assert fetcher.calls == []


def test_fetch_refuse_un_chemin_hors_sources(tmp_path: Path) -> None:
    entry = {
        "candidate_id": "c1",
        "document_title": "Programme",
        "type": "pdf",
        "source_url": URL,
        "local_path": "sources/../../hors.pdf",
        "sha256": hashlib.sha256(PDF).hexdigest(),
        "retrieved_at": "2026-11-19",
    }
    election = write_corpus_election(tmp_path, [entry])
    fetcher = FakeFetcher({URL: PDF})
    with pytest.raises(SourceError, match="hors de sources"):
        fetch_corpus(election, fetcher=fetcher)
    assert fetcher.calls == []
    assert not (tmp_path / "hors.pdf").exists()


def test_aucun_fichier_temporaire_restant(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    _add(election, FakeFetcher({URL: PDF}))
    assert not list((election / "sources").rglob("*.part"))
