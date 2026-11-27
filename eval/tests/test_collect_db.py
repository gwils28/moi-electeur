"""Collecte sur une vraie base (marqueur `db`) : le classement RRF reproduit `/retrieve`."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

from moi_electeur_eval.collect import collect
from moi_electeur_eval.recall import evaluate
from moi_electeur_eval.smoke import ExpectedChunk, Question
from moi_electeur_rag.db import connect, migrate
from moi_electeur_rag.embedding import FakeEmbedder
from moi_electeur_rag.retrieve import NotIndexed, retrieve
from moi_electeur_rag.store import index_election

pytestmark = pytest.mark.db

ELECTION = "test-eval"
THEMES = [("social", "retraite santé"), ("ecologie", "nucléaire climat")]
TEXTS = {
    "alice": [
        "Nous ramènerons la retraite à 60 ans pour les salariés.",
        "Les centrales nucléaires seront fermées en dix ans.",
        "Les logements sociaux seront construits dans chaque commune.",
    ],
    "bruno": [
        "Le nucléaire est la base de notre énergie : six réacteurs neufs.",
        "Les impôts de production des entreprises baisseront.",
    ],
    "david": ["Les éoliennes défigurent nos paysages et nos campagnes."],
}


def _chunks() -> list[dict[str, Any]]:
    out = []
    for cand, texts in TEXTS.items():
        sha = (cand[0] * 64)[:64]
        for n, text in enumerate(texts):
            out.append(
                {
                    "id": f"{sha[:12]}-{n:04d}",
                    "election_id": ELECTION,
                    "candidate_id": cand,
                    "document_title": f"Programme {cand}",
                    "source_url": f"https://example.org/{cand}.pdf",
                    "document_sha256": sha,
                    "page_number": n + 1,
                    "page_end": n + 1,
                    "section_title": None,
                    "theme": None,
                    "text": text,
                    "token_count": len(text.split()),
                    "corpus_version": "1111111111111111",
                }
            )
    return out


def _exp(chunk_id: str, cand: str, page: int) -> ExpectedChunk:
    return ExpectedChunk(chunk_id, f"Programme {cand}", str(page))


QUESTIONS = [
    Question(
        "q-nuc",
        "Que proposent les candidats sur le nucléaire ?",
        "silence",
        "ecologie",
        {
            "alice": [_exp("aaaaaaaaaaaa-0001", "alice", 2)],
            "bruno": [_exp("bbbbbbbbbbbb-0000", "bruno", 1)],
        },
        ["david"],
    ),
    Question("q-vote", "Pour qui voter ?", "recommandation", None),
]


@pytest.fixture
def conn(db_dsn: str) -> Iterator[psycopg.Connection[Any]]:
    migrate(db_dsn)
    with connect(db_dsn) as c:
        c.execute("TRUNCATE chunks, corpus_versions CASCADE")
        c.commit()
        index_election(
            c, election_id=ELECTION, chunks=_chunks(), embedder=FakeEmbedder(), themes=THEMES
        )
        yield c


def test_rrf_identique_a_retrieve(conn: psycopg.Connection[Any]) -> None:
    got = collect(conn, FakeEmbedder(), election_id=ELECTION, questions=QUESTIONS, keep=6)
    assert got["candidates"] == ["alice", "bruno", "david"]
    assert set(got["rankings"]) == {
        "semantique",
        "plein_texte",
        "rrf",
        "plein_texte_brut",
        "rrf_brut",
    }
    for q in QUESTIONS:
        served = retrieve(conn, FakeEmbedder(), election_id=ELECTION, question=q.question, k=4)
        for block in served["candidates"]:
            ids = [r["chunk"]["id"] for r in block["chunks"]]
            assert got["rankings"]["rrf"][q.id][block["candidate_id"]][:4] == ids
    sim = got["similarity"]["q-nuc"]
    assert sim["min"] <= sim["p50"] <= sim["p90"] <= sim["max"]
    assert sim["relevant_mean"] is not None and sim["relevant_mean"] > sim["irrelevant_mean"]
    report = evaluate(QUESTIONS, got["rankings"]["rrf"], got["candidates"], k=4)
    assert report.full_coverage
    assert report.questions[0].recall == 1.0  # chaque candidat a au plus 3 extraits


def test_plein_texte_servi_sans_lexeme_omnipresent(conn: psycopg.Connection[Any]) -> None:
    # « Les » donne le lexème `le`, présent dans presque tous les extraits jouets : le plein texte
    # servi ne garde que les extraits qui contiennent un mot discriminant (« nucléaire ») ; la
    # référence brute de M2b les gardait tous.
    got = collect(conn, FakeEmbedder(), election_id=ELECTION, questions=QUESTIONS[:1], keep=6)
    served = got["rankings"]["plein_texte"]["q-nuc"]
    assert served["alice"] == ["aaaaaaaaaaaa-0001"]
    assert served["bruno"] == ["bbbbbbbbbbbb-0000"]
    assert served["david"] == []
    assert len(got["rankings"]["plein_texte_brut"]["q-nuc"]["alice"]) > 1


def test_attendu_incoherent_refuse(conn: psycopg.Connection[Any]) -> None:
    bad = [Question("q", "?", "theme", None, {"alice": [_exp("inconnu-0000", "alice", 1)]})]
    with pytest.raises(ValueError, match="extrait inconnu"):
        collect(conn, FakeEmbedder(), election_id=ELECTION, questions=bad)


def test_election_non_indexee(conn: psycopg.Connection[Any]) -> None:
    with pytest.raises(NotIndexed):
        collect(conn, FakeEmbedder(), election_id="absente", questions=QUESTIONS)
