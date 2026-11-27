# Front Next.js (build de production servi par `next start`).
# Étape 1 : JSON statiques validés produits par le pipeline (D5 : non commités).
FROM python:3.12-slim AS data
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
WORKDIR /app
# `pipeline build` seul (point d'entrée autonome) : ni torch, ni service de recherche, ni CLI.
# Versions minimales de pipeline/pyproject.toml.
RUN uv pip install --system --no-cache "jsonschema>=4.26" "referencing>=0.37" "numpy>=2.5" \
    "rfc3339-validator>=0.1.4" "rfc3986-validator>=0.1.1"
# pnpm-workspace.yaml : repère de la racine du dépôt (moi_electeur_pipeline.paths).
COPY pnpm-workspace.yaml ./
COPY pipeline/src pipeline/src
COPY schemas schemas
COPY data data
RUN PYTHONPATH=pipeline/src python -m moi_electeur_pipeline.build

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
