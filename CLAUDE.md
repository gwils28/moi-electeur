# Moi Électeur

Boussole électorale + explorateur RAG des programmes officiels. Spécification : @SPEC.md. Plan en cours : `PLAN.md`. Notes d'implémentation : `docs/notes-implementation.md`.

## Règles non négociables
- Les réponses au questionnaire, les poids et (X_user, Y_user) ne quittent **jamais** le navigateur. Aucun appel réseau dans `packages/engine` (vérifié par ESLint et `packages/engine/test/no-io.test.ts`).
- Ne jamais logguer le contenu des questions du chat (donnée d'opinion, RGPD art. 9).
- Le front ne charge que des positions/mesures au statut `validated` ou `corrected`.
- Aucun texte produit par l'app ne classe un candidat (« meilleur », « plus crédible »…). Ordre des candidats aléatoire.
- Les (x, y) des candidats sont **calculés**, jamais saisis à la main.
- Types de données : source unique = `schemas/*.schema.json`. Ne pas dupliquer à la main en TS/Pydantic.

## Façon de travailler
- Phases : explorer → lever les inconnues → plan (`PLAN.md`, annoté par l'humain) → implémenter avec tests → valider → l'humain commite.
- Le moteur de calcul s'écrit test d'abord ; ne pas modifier un test pour le faire passer sans le signaler.
- Consigner dans `docs/notes-implementation.md` tout écart au plan et tout choix conservateur.
- Ne pas commiter ni pousser : préparer le diff, lancer les contrôles, proposer un message Conventional Commits.
- Rien n'est « fini » sans preuve : sortie de test ou commande lancée.
- Tiret cadratin (U+2014) interdit partout (code, commentaires, docs, réponses) : virgule, deux-points, parenthèses ou tiret simple "-". Imposé par le hook `.claude/hooks/no-em-dash.py`.

## Commandes
- Installer : `pnpm install && uv sync --all-packages`
- Tout contrôler (JS) : `pnpm check` (lint, typecheck, tests, hygiène)
- Tests JS : `pnpm test` ; E2E : `pnpm --filter @moi-electeur/web e2e`
- Tests Python : `uv run --project pipeline pytest -q pipeline` (idem `services/rag`, `eval`, `notebooks`)
- Lint Python : `uv run --project pipeline ruff check . && uv run --project pipeline ruff format --check . && uv run --project pipeline mypy pipeline/src services/rag/src eval/src`
- Corpus (E = `data/elections/<id>`) : `uv run pipeline add-source E <candidat> <url> --title …` puis `fetch E`, `extract E`, `chunk E` (fichiers dans `E/sources/`, ignoré par git)
- Index RAG (base de `DATABASE_URL`, défaut : Postgres du compose) : `uv run pipeline db-migrate` puis `uv run pipeline index E --model multilingual-e5-large|bge-m3` (défaut e5, PLAN D37) (poids dans `models/`, ignoré par git) ; tests `db` : `docker compose up -d db` avant pytest
- Données : `uv run pipeline validate` ; démo : `uv run pipeline make-demo [--check]` ; JSON du front : `uv run pipeline build` (lancé par `pnpm dev`/`pnpm build` du web)
- Fixture croisée Python/TS du moteur : `uv run pipeline engine-fixtures [--check]`
- Types depuis `schemas/` : `pnpm gen:types` (TS) et `uv run pipeline gen-models [--check]` (Pydantic)
- Notebooks : `uv run --project notebooks marimo edit notebooks/<fichier>.py`
- Stack locale : `docker compose up -d --build --wait` (web :3000, rag :8000, db :5432)
- Production : `docker compose -f docker-compose.prod.yml --env-file .env up -d --build --wait` puis `scripts/deploy-check.sh https://<domaine>` (guide : `docs/deploiement.md`)

## Compaction
En cas de compaction, conserver : fichiers modifiés, commandes de test et leur dernier résultat, décisions de modélisation (formules, schémas), points ouverts de SPEC.md § 15.

Ligne témoin : terminer chaque réponse finale qui modifie du code par « 🧭 ».
