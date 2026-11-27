"""API FastAPI : /retrieve, /health, et aucune trace de la question dans les logs (SPEC § 6.3)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from moi_electeur_rag import app as app_module
from moi_electeur_rag.db import connect, migrate
from moi_electeur_rag.embedding import FakeEmbedder
from moi_electeur_rag.store import index_election

QUESTION = "Quelle est votre position secrète sur la retraite ?"


@pytest.fixture
def client(db_dsn: str) -> Iterator[TestClient]:
    from test_store_retrieve import CORPUS, ELECTION, THEMES

    migrate(db_dsn)
    with connect(db_dsn) as c:
        c.execute("TRUNCATE chunks, corpus_versions CASCADE")
        c.commit()
        index_election(
            c, election_id=ELECTION, chunks=CORPUS, embedder=FakeEmbedder(), themes=THEMES
        )

    def conn_override() -> Iterator[psycopg.Connection[Any]]:
        with connect(db_dsn) as c:
            yield c

    app = app_module.app
    app.dependency_overrides[app_module.get_conn] = conn_override
    app.dependency_overrides[app_module.get_embedder] = FakeEmbedder
    app.dependency_overrides[app_module.get_db_probe] = lambda: app_module.make_probe(db_dsn)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.db
def test_retrieve(client: TestClient) -> None:
    response = client.post("/retrieve", json={"election_id": "test-2022", "question": QUESTION})
    assert response.status_code == 200
    body = response.json()
    assert body["election_id"] == "test-2022"
    assert {c["candidate_id"] for c in body["candidates"]} == {"alice", "bruno", "david"}


@pytest.mark.db
def test_retrieve_election_inconnue_404(client: TestClient) -> None:
    response = client.post("/retrieve", json={"election_id": "inconnue", "question": QUESTION})
    assert response.status_code == 404
    assert QUESTION not in response.text


@pytest.mark.db
def test_aucune_trace_de_la_question(
    client: TestClient, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(logging.DEBUG)
    client.post("/retrieve", json={"election_id": "test-2022", "question": QUESTION})
    client.post("/retrieve", json={"election_id": "inconnue", "question": QUESTION})
    out = capsys.readouterr()
    assert "secrète" not in caplog.text
    assert "secrète" not in out.out + out.err


@pytest.mark.db
def test_erreur_interne_sans_trace_de_la_question(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_a: Any, **_k: Any) -> None:
        raise RuntimeError(f"échec avec {QUESTION}")

    monkeypatch.setattr(app_module, "retrieve", boom)
    caplog.set_level(logging.DEBUG)
    response = client.post("/retrieve", json={"election_id": "test-2022", "question": QUESTION})
    assert response.status_code == 500
    out = capsys.readouterr()
    assert "secrète" not in caplog.text + out.out + out.err + response.text


@pytest.mark.db
def test_health_avec_base(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_sans_base() -> None:
    app = app_module.app
    unreachable = "postgresql://personne@127.0.0.1:1/aucune"
    app.dependency_overrides[app_module.get_db_probe] = lambda: app_module.make_probe(unreachable)
    try:
        response = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


def test_requete_invalide_422() -> None:
    response = TestClient(app_module.app).post(
        "/retrieve", json={"election_id": "x", "question": ""}
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"election_id": "test-2022", "question": "retraite\u0000"},  # NUL : refusé par PostgreSQL
        {"election_id": "test-2022", "question": "retraite", "k": 0},
        {"election_id": "test-2022", "question": "retraite", "k": 11},
        {"election_id": "test-2022", "question": "retraite", "theme": "Pas un slug"},
        {"election_id": "test-2022", "question": "x" * 501},
    ],
)
def test_entrees_invalides_422(payload: dict[str, Any]) -> None:
    response = TestClient(app_module.app).post("/retrieve", json=payload)
    assert response.status_code == 422


@pytest.mark.db
def test_candidats_en_double_dedoublonnes(client: TestClient) -> None:
    response = client.post(
        "/retrieve",
        json={
            "election_id": "test-2022",
            "question": "énergie",
            "candidate_ids": ["bruno", "bruno"],
        },
    )
    assert response.status_code == 200
    assert [c["candidate_id"] for c in response.json()["candidates"]] == ["bruno"]


def test_panne_dune_dependance_sans_trace(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """Base injoignable ou modèle absent : 500 JSON, journal réduit au type de l'erreur."""

    def broken_conn() -> Iterator[psycopg.Connection[Any]]:
        raise psycopg.OperationalError(f"connexion à postgresql://secret@db refusée ({QUESTION})")
        yield  # pragma: no cover

    app = app_module.app
    app.dependency_overrides[app_module.get_conn] = broken_conn
    app.dependency_overrides[app_module.get_embedder] = FakeEmbedder
    caplog.set_level(logging.DEBUG)
    try:
        response = TestClient(app).post(
            "/retrieve", json={"election_id": "test-2022", "question": QUESTION}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json() == {"detail": "erreur interne"}
    out = capsys.readouterr()
    logged = caplog.text + out.out + out.err
    assert "OperationalError" in caplog.text
    for secret in ("secrète", "postgresql://secret"):
        assert secret not in logged + response.text


def test_faux_embedder_interdit_dans_le_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_MODEL", "fake")
    with pytest.raises(RuntimeError, match="interdit"):
        app_module.get_embedder()
