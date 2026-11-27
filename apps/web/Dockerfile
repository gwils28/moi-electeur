# Front Next.js (build de production servi par `next start`).
# Étape 1 : JSON statiques validés produits par le pipeline (D5 : non commités).
FROM python:3.12-slim AS data
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version pnpm-workspace.yaml ./
COPY pipeline pipeline
COPY services/rag/pyproject.toml services/rag/pyproject.toml
COPY eval/pyproject.toml eval/pyproject.toml
COPY notebooks/pyproject.toml notebooks/pyproject.toml
COPY schemas schemas
COPY data data
RUN uv sync --frozen --no-dev --package moi-electeur-pipeline && uv run --no-sync pipeline build

FROM node:24-slim AS build
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/engine/package.json packages/engine/package.json
COPY packages/schemas-ts/package.json packages/schemas-ts/package.json
RUN pnpm install --frozen-lockfile
COPY packages packages
# Schémas (validation de /api/ask) et prompts (prompt système, mots interdits) : lus par la route.
COPY schemas schemas
COPY prompts prompts
# Méthodologie et déclaration d'accessibilité : lues par les pages /methodologie et /accessibilite.
COPY docs/methodologie.md docs/accessibilite.md docs/
COPY apps/web apps/web
COPY --from=data /app/apps/web/public/data apps/web/public/data
# Données déjà produites par l'étape « data » : on saute le prebuild (pnpm data).
RUN cd apps/web && node_modules/.bin/next build

FROM node:24-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app /app
WORKDIR /app/apps/web
USER node
EXPOSE 3000
CMD ["node_modules/.bin/next", "start"]
