"""Application FastAPI du service de retrieval (PLAN § 4.4).

Règle : ne jamais logguer le contenu des questions (donnée d'opinion, RGPD art. 9). Le journal
d'accès d'uvicorn est désactivé (`--no-access-log`). Toute erreur non prévue (endpoint,
dépendances : base, modèle ; validation de la réponse) est interceptée par un middleware qui la
journalise par son seul type et renvoie un 500 JSON : uvicorn ne reçoit jamais l'exception, donc
n'écrit ni trace ni message (qui pourraient contenir la question, des extraits ou le DSN).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable, Iterator
from typing import Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from .db import connect, database_url
from .embedding import DEFAULT_MODEL, Embedder
from .embedding import get_embedder as _load_embedder
from .generated.retrieve_request_schema import RetrieveRequest
from .generated.retrieve_response_schema import RetrieveResponse
from .retrieve import NotIndexed, retrieve

logger = logging.getLogger("moi_electeur_rag")

app = FastAPI(title="moi-electeur-rag", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def contain_errors(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error(
            "%s %s : erreur interne (%s)", request.method, request.url.path, type(exc).__name__
        )
        return JSONResponse({"detail": "erreur interne"}, status_code=500)


def validated_request(request: RetrieveRequest) -> RetrieveRequest:
    """Seul porteur du corps : la base et le modèle n'en dépendent que pour ne pas être sollicités
    par une requête invalide (FastAPI résout les dépendances avant de lever l'erreur de
    validation, mais saute une dépendance dont une sous-dépendance est en erreur : 422 garanti
    même base arrêtée, et aucune connexion ouverte pour rien)."""
    return request


def get_embedder(_: RetrieveRequest = Depends(validated_request)) -> Embedder:  # noqa: B008
    name = os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL)
    if name == "fake":  # réservé aux tests (injecté par dependency_overrides)
        raise RuntimeError("EMBEDDING_MODEL=fake interdit dans le service")
    return _load_embedder(name)


def get_conn(
    _: RetrieveRequest = Depends(validated_request),  # noqa: B008
) -> Iterator[psycopg.Connection[Any]]:
    with connect() as conn:
        yield conn


def make_probe(dsn: str) -> Callable[[], bool]:
    def probe() -> bool:
        try:
            with psycopg.connect(dsn, connect_timeout=2) as conn:
                conn.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

    return probe


def get_db_probe() -> Callable[[], bool]:
    return make_probe(database_url())


@app.get("/health")
def health(probe: Callable[[], bool] = Depends(get_db_probe)) -> JSONResponse:  # noqa: B008
    if probe():
        return JSONResponse({"status": "ok", "database": "ok"})
    return JSONResponse({"status": "degraded", "database": "unavailable"}, status_code=503)


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve_endpoint(
    request: RetrieveRequest = Depends(validated_request),  # noqa: B008
    conn: psycopg.Connection[Any] = Depends(get_conn),  # noqa: B008
    embedder: Embedder = Depends(get_embedder),  # noqa: B008
) -> dict[str, Any]:
    try:
        return retrieve(
            conn,
            embedder,
            election_id=request.election_id.root,
            question=request.question,
            candidate_ids=[c.root for c in request.candidate_ids or []] or None,
            theme=request.theme.root if request.theme else None,
            k=request.k or 4,
        )
    except NotIndexed as exc:
        raise HTTPException(status_code=404, detail="élection non indexée") from exc
