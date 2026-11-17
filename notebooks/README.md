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
