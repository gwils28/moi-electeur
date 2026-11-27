# Notebooks R&D

Notebooks [marimo](https://marimo.io) (fichiers `.py` purs, diffables, exécutés par la CI) qui
expliquent et tracent chaque choix de conception du moteur, de l'intelligence (RAG, LLM) et de
l'analytique (ACP, backtest). Voir PLAN § 1 bis.

- Ouvrir : `uv run --project notebooks marimo edit notebooks/<fichier>.py`
- Exécuter tous les notebooks : `uv run --project notebooks pytest -q notebooks`
- Nouveau notebook : copier `_template.py` en `<jalon>-<nn>-<sujet>.py` et respecter ses 6 sections.

| Notebook | Sujet | Statut |
|---|---|---|
| [m0-01-donnees-demo.py](m0-01-donnees-demo.py) | Construction et contrôle des données fictives | décision prise |
| [m1-01-proximite.py](m1-01-proximite.py) | Score de proximité (Manhattan pondérée), effet des poids, D2 | décision prise |
| [m1-02-projection-a.py](m1-02-projection-a.py) | Projection mode A (affirmations taguées) | décision prise |
| [m1-03-acp-mode-b.py](m1-03-acp-mode-b.py) | ACP mode B, orientation D3, échelle D4 | décision prise |
| [m2-01-extraction-chunks.py](m2-01-extraction-chunks.py) | Qualité d'extraction, tailles des extraits, cas limites, couverture par candidat | décision prise |
| [m2-02-embeddings.py](m2-02-embeddings.py) | bge-m3 contre multilingual-e5-large sur le jeu de fumée | décision provisoire |
| [m2-03-retrieval-rrf.py](m2-03-retrieval-rrf.py) | Sémantique seule, plein texte seul, RRF ; diagnostic du plein texte | décision à trancher |
| [m2-04-prompt-neutralite.py](m2-04-prompt-neutralite.py) | Neutralité et silences sur deux réponses réelles enregistrées | exploration |

## Fixtures (`fixtures/`)

La CI n'a ni la base, ni les poids des modèles, ni les PDF (`data/elections/*/sources/`, ignoré
par git) : les notebooks M2 lisent des fixtures versionnées, petites, produites depuis les
données réelles. Les régénérer après une réindexation ou une modification du jeu de fumée :

| Fixture | Contenu | Commande |
|---|---|---|
| `m2-corpus-stats.json` | statistiques agrégées par document et par candidat, tailles des extraits, cas limites (aucun texte de programme hors exemples de 60 caractères) | `uv run --project eval moi-electeur-eval corpus-stats` |
| `m2-retrieval-smoke.json` | pour chaque modèle, méthode, question et candidat : les 6 premiers extraits (indices dans `chunk_ids`), similarités résumées, lexèmes de la requête | `docker compose up -d db` puis `HF_HUB_OFFLINE=1 uv run --project eval moi-electeur-eval retrieval` |
| `m2-ask-nucleaire-*.sse`, `m2-ask-runs.json` | deux réponses réelles de `/api/ask` (Haiku 5.5, Sonnet 5.5) et leur coût | enregistrées à la main le 2026-11-27 (0,14 $ au total) ; ne pas rejouer en CI |
