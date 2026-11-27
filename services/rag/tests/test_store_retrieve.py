"""Migrations, indexation et récupération sur une vraie base (marqueur `db`, PLAN D18-D19)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

from moi_electeur_rag.db import connect, migrate
from moi_electeur_rag.embedding import FakeEmbedder
from moi_electeur_rag.retrieve import NotIndexed, retrieve
from moi_electeur_rag.store import index_election

pytestmark = pytest.mark.db

ELECTION = "test-2022"
V1 = "1111111111111111"
V2 = "2222222222222222"
THEMES = [
    ("social", "retraite santé hôpital logement école"),
    ("ecologie", "climat énergie nucléaire éolien transport"),
]


def make_chunk(candidate: str, n: int, text: str, version: str = V1) -> dict[str, Any]:
    sha = (candidate[0] * 64)[:64] if candidate[0] in "abcdef" else "0" * 64
    return {
        "id": f"{sha[:12]}-{n:04d}",
        "election_id": ELECTION,
        "candidate_id": candidate,
        "document_title": f"Programme {candidate}",
        "source_url": f"https://web.archive.org/web/2022id_/https://{candidate}.fr/p.pdf",
        "document_sha256": sha,
        "page_number": n + 1,
        "page_end": n + 1,
        "section_title": None,
        "theme": None,
        "text": text,
        "token_count": len(text.split()),
        "corpus_version": version,
    }


CORPUS = [
    make_chunk("alice", 0, "Nous ramènerons la retraite à 60 ans pour tous les salariés."),
    make_chunk("alice", 1, "Le climat exige de fermer les centrales à charbon."),
    make_chunk("alice", 2, "Nous construirons des logements sociaux dans chaque commune."),
    make_chunk("bruno", 0, "Le nucléaire est la base de notre énergie : six réacteurs neufs."),
    make_chunk("bruno", 1, "Nous baisserons les impôts de production des entreprises."),
    make_chunk("david", 0, "Les éoliennes défigurent nos paysages et nos campagnes."),
]


@pytest.fixture
def conn(db_dsn: str) -> Iterator[psycopg.Connection[Any]]:
    migrate(db_dsn)
    with connect(db_dsn) as c:
        c.execute("TRUNCATE chunks, corpus_versions CASCADE")
        c.commit()
        yield c


def _index(conn: psycopg.Connection[Any], chunks: list[dict[str, Any]], **kw: Any) -> Any:
    return index_election(
        conn, election_id=ELECTION, chunks=chunks, embedder=FakeEmbedder(), themes=THEMES, **kw
    )


def _ask(conn: psycopg.Connection[Any], question: str, **kw: Any) -> dict[str, Any]:
    return retrieve(conn, FakeEmbedder(), election_id=ELECTION, question=question, **kw)


def test_migrations_rejouables(db_dsn: str) -> None:
    migrate(db_dsn)
    migrate(db_dsn)
    with connect(db_dsn) as c:
        rows = c.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    assert [r["version"] for r in rows] == ["001_init"]


def test_index_puis_retrieve_couvre_chaque_candidat(conn: psycopg.Connection[Any]) -> None:
    report = _index(conn, CORPUS)
    assert report.n_chunks == 6
    assert report.corpus_version == V1

    result = _ask(conn, "Que proposent-ils sur la retraite ?", k=2)
    assert result["corpus_version"] == V1
    assert result["model"] == "fake"
    assert [c["candidate_id"] for c in result["candidates"]] == ["alice", "bruno", "david"]
    by_cand = {c["candidate_id"]: c["chunks"] for c in result["candidates"]}
    # Chaque candidat est présent même sans aucun mot commun avec la question.
    assert len(by_cand["bruno"]) == 2
    assert len(by_cand["david"]) == 1
    top = by_cand["alice"][0]
    assert "retraite" in top["chunk"]["text"]
    assert top["lexical_rank"] == 1
    assert top["semantic_rank"] == 1
    assert top["score"] == pytest.approx(2 / 61)
    assert top["chunk"]["document_title"] == "Programme alice"


def test_filtre_candidats(conn: psycopg.Connection[Any]) -> None:
    _index(conn, CORPUS)
    result = _ask(conn, "énergie", candidate_ids=["bruno", "inconnu"])
    assert [c["candidate_id"] for c in result["candidates"]] == ["bruno", "inconnu"]
    assert result["candidates"][1]["chunks"] == []


def test_filtre_theme(conn: psycopg.Connection[Any]) -> None:
    _index(conn, CORPUS, theme_margin=0.0)
    result = _ask(conn, "énergie", theme="ecologie")
    themes = {ch["chunk"]["theme"] for c in result["candidates"] for ch in c["chunks"]}
    assert themes == {"ecologie"}


def test_reindexation_remplace_lancienne_version(conn: psycopg.Connection[Any]) -> None:
    _index(conn, CORPUS)
    new = [make_chunk("alice", 0, "Texte révisé sur la retraite.", V2)]
    report = _index(conn, new)
    assert report.corpus_version == V2
    n = conn.execute("SELECT count(*) AS n FROM chunks").fetchone()
    assert n is not None and n["n"] == 1
    result = _ask(conn, "retraite")
    assert result["corpus_version"] == V2
    assert [c["candidate_id"] for c in result["candidates"]] == ["alice"]


def test_index_refuse_des_versions_melangees(conn: psycopg.Connection[Any]) -> None:
    with pytest.raises(ValueError, match="version"):
        _index(conn, [CORPUS[0], make_chunk("bruno", 3, "x", V2)])


def test_election_non_indexee(conn: psycopg.Connection[Any]) -> None:
    with pytest.raises(NotIndexed):
        _ask(conn, "retraite")


def test_question_sans_mot_plein(conn: psycopg.Connection[Any]) -> None:
    """Une question faite de mots vides n'a pas de requête plein texte : seul le sémantique joue."""
    _index(conn, CORPUS)
    result = _ask(conn, "et le la", k=1)
    for c in result["candidates"]:
        assert c["chunks"][0]["lexical_rank"] is None
        assert c["chunks"][0]["semantic_rank"] == 1


def test_index_refuse_un_caractere_nul_avant_tout_calcul(conn: psycopg.Connection[Any]) -> None:
    class Exploding(FakeEmbedder):
        def embed_documents(self, texts: Any) -> Any:
            raise AssertionError("aucun calcul ne doit être lancé")

    bad = make_chunk("alice", 9, "texte\x00corrompu")
    with pytest.raises(ValueError, match="NUL"):
        index_election(
            conn, election_id=ELECTION, chunks=[bad], embedder=Exploding(), themes=THEMES
        )


@pytest.mark.db
def test_migrations_sur_base_neuve_et_concurrentes(db_dsn: str) -> None:
    """Chaque migration dans sa transaction ; deux `migrate` simultanés ne se gênent pas.

    `db_dsn` n'est demandé que pour ignorer le test sans base en local (échec en CI)."""
    import threading

    from moi_electeur_rag.testing import temporary_database

    with temporary_database() as dsn:
        results: list[list[str]] = []
        threads = [threading.Thread(target=lambda: results.append(migrate(dsn))) for _ in range(2)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert sorted(results) == [[], ["001_init"]]
        assert migrate(dsn) == []


def test_index_signale_la_version_remplacee(conn: psycopg.Connection[Any]) -> None:
    assert _index(conn, CORPUS).replaced_version is None
    assert _index(conn, CORPUS).replaced_version is None
    report = _index(conn, [make_chunk("alice", 0, "Nouveau texte.", V2)])
    assert report.replaced_version == V1


def test_mot_present_dans_la_plupart_des_extraits_ignore_en_plein_texte(
    conn: psycopg.Connection[Any],
) -> None:
    """En configuration `french`, « les » devient le lexème `le`, non retiré comme mot vide : présent
    dans presque tous les extraits, il noyait la requête en OU (M2d : RRF sous la sémantique
    seule). Les lexèmes présents dans plus de la moitié des extraits sont ignorés."""
    _index(
        conn,
        [
            make_chunk(
                "alice", 0, "Les salariés, les ouvriers, les cadres, les artisans et les jeunes."
            ),
            make_chunk("alice", 1, "Nous ramènerons la retraite à 60 ans."),
            make_chunk("bruno", 0, "Les impôts de production des entreprises baisseront."),
            make_chunk("david", 0, "Les éoliennes défigurent nos paysages."),
        ],
    )
    result = _ask(conn, "Que proposent les candidats sur les retraites ?", k=2)
    alice = {c["chunk"]["id"][-1]: c for c in result["candidates"][0]["chunks"]}
    assert alice["1"]["lexical_rank"] == 1
    # Le seul mot commun (« les ») ne suffit plus à faire entrer un extrait dans le plein texte.
    assert alice["0"]["lexical_rank"] is None
    for c in result["candidates"][1:]:
        assert all(ch["lexical_rank"] is None for ch in c["chunks"])


def test_mot_discriminant_garde_meme_sil_est_frequent_chez_un_candidat(
    conn: psycopg.Connection[Any],
) -> None:
    """La fréquence est calculée sur toute l'élection, pas par candidat."""
    _index(
        conn,
        [
            make_chunk("alice", 0, "La retraite à 60 ans."),
            make_chunk("alice", 1, "Une retraite digne pour tous."),
            make_chunk("bruno", 0, "Les impôts baisseront."),
            make_chunk("bruno", 1, "Des entreprises plus libres."),
            make_chunk("david", 0, "Des éoliennes partout."),
        ],
    )
    result = _ask(conn, "retraite", k=2)
    alice = result["candidates"][0]["chunks"]
    assert {c["lexical_rank"] for c in alice} == {1, 2}
