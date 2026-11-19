# Service RAG (FastAPI). Torch CPU uniquement ; les poids des modèles sont montés en volume (/models), pas inclus dans l'image.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY pipeline/pyproject.toml pipeline/pyproject.toml
COPY eval/pyproject.toml eval/pyproject.toml
COPY notebooks/pyproject.toml notebooks/pyproject.toml
COPY services/rag services/rag
# --no-cache : le cache de uv (plus de 1 Go avec torch) ne reste pas dans la couche.
RUN uv sync --frozen --no-dev --no-cache --package moi-electeur-rag
RUN useradd --system --uid 1001 app
USER app
EXPOSE 8000
CMD ["uvicorn", "moi_electeur_rag.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
