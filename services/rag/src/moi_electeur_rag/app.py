"""Application FastAPI du service de retrieval.

Règle : ne jamais logguer le contenu des questions (donnée d'opinion, RGPD art. 9).
"""

from fastapi import FastAPI

app = FastAPI(title="moi-electeur-rag", docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
