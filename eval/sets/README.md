# Jeu d'évaluation complet (M4)

`questions-2022.jsonl` : 60 questions sur le corpus `fr-presidentielle-2022` (PLAN D36), même
format que le jeu de fumée (`eval/smoke/README.md`), dont il est un sur-ensemble : les 15
premières lignes sont les questions du jeu de fumée, inchangées (les notebooks M2 et leur fixture
en dépendent).

| Type | Nombre | Rôle |
|---|---|---|
| `theme` | 17 | chaque candidat attendu porte une proposition sur le sujet |
| `silence` | 39 | au moins un candidat ne dit rien du sujet ; dont q53 (changement d'heure), qu'aucun programme ne traite : tout contenu attribué à un candidat y est une hallucination |
| `recommandation` | 4 | demande d'orientation du vote ou de classement : la réponse attendue est un refus |

**Annotation** (2026-11-27) : 45 questions nouvelles annotées par trois agents en parallèle,
même méthode que le jeu de fumée (recherche par mots-clés, synonymes et sigles, lecture des
passages), césures du PDF (« jeux-vidéos ») prises en compte pour vérifier les silences ; cas
douteux expliqués dans `note`. Biais connus : favorable au plein texte ; « attendu » au sens
d'une proposition, y compris une position contre (q36 défense européenne, q49 vote des
étrangers) ; le corpus de melenchon est la version abrégée de son programme.

Contrôle : `uv run --project eval moi-electeur-eval check-smoke --questions eval/sets/questions-2022.jsonl`.
Recherche : `HF_HUB_OFFLINE=1 uv run --project eval moi-electeur-eval retrieval --questions eval/sets/questions-2022.jsonl --out notebooks/fixtures/m4-retrieval-60.json`.
