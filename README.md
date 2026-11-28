# Moi Électeur

Boussole électorale et interrogatoire des programmes officiels des candidats, à commencer par la présidentielle 2027.

- **Boussole** : questionnaire, score de proximité et échiquier 2D, calculés entièrement dans le navigateur (aucune réponse n'est envoyée au serveur).
- **Interrogatoire** (page d'accueil `/`, fonction centrale) : questions ouvertes en langage naturel, réponses neutres sourcées par des citations des programmes officiels (RAG + Claude).

Spécification : [SPEC.md](SPEC.md). Plan : [PLAN.md](PLAN.md). Statut : socle en place (jalon M0), données de démonstration fictives.

## Démarrage rapide
Prérequis : Node 24, pnpm, [uv](https://docs.astral.sh/uv/), Docker.

```bash
pnpm install && uv sync --all-packages
pnpm check                              # lint, types, tests JS, hygiène
uv run pipeline validate                # validation des données
docker compose up -d --build --wait     # web http://localhost:3000, rag http://localhost:8001/health
```

Les notebooks R&D qui expliquent les choix de conception sont dans [notebooks/](notebooks/).

## Licences
- Code : [AGPL-3.0](LICENSE)
- Données dérivées (affirmations, positions, mesures, jeux d'évaluation) : CC BY-SA 4.0
