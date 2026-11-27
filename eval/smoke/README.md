# Jeu de fumée du retrieval

`questions-2022.jsonl` : 15 questions sur le corpus `fr-presidentielle-2022` (PLAN § 4.7), qui
servent de test de non-régression de la recherche (rappel@k, sans LLM). 10 questions
thématiques, 3 pièges sur des silences et 2 demandes de recommandation. Le jeu complet
(environ 60 questions) arrive en M4.

## Format (une question JSON par ligne)

| Champ | Type | Sens |
|---|---|---|
| `id` | texte | identifiant stable (`qNN-sujet`) |
| `question` | texte | question posée telle quelle à `/retrieve` |
| `kind` | `theme`, `silence` ou `recommandation` | `silence` : piège, au moins un candidat ne dit rien du sujet ; `recommandation` : demande d'orientation du vote, sans attendu |
| `theme` | identifiant de thème ou `null` | thème de `election_config.json` (indicatif, non utilisé comme filtre) |
| `expected` | objet `{candidate_id: [extrait…]}` | candidats qui traitent le sujet et leurs extraits pertinents ; chaque extrait : `chunk_id`, `document_title`, `pages` (`"7"` ou `"7-8"`) |
| `silent` | liste de `candidate_id` | candidats dont aucun extrait ne traite le sujet (vérifié par recherche dans tout le corpus) ; non vide si et seulement si `kind = silence` |
| `note` | texte | critère d'annotation, faux amis, candidats volontairement non attendus |

Un candidat absent de `expected` et de `silent` n'est pas évalué (il évoque le sujet sans
proposition, ou de façon trop indirecte). Les demandes de recommandation n'ont ni `expected` ni
`silent` : seule la couverture (au moins un extrait par candidat) est contrôlée ; la réponse
attendue du chat est un refus d'orienter le vote.

## Construction

Attendus déterminés en **lisant le corpus réel** (`sources/chunks.jsonl`) : recherche par
mots-clés et synonymes dans tous les extraits, lecture des passages, sélection des extraits qui
portent une proposition sur le sujet (1 à 5 par candidat). Biais connu : une annotation partie de
mots-clés favorise le plein texte et peut omettre un extrait pertinent formulé autrement.

Les `chunk_id` dépendent du découpage : après un nouveau `pipeline chunk`, lancer
`uv run --project eval moi-electeur-eval check-smoke`, qui signale tout extrait disparu, déplacé
ou attribué à un autre candidat.

## Mesure

    uv run --project eval moi-electeur-eval retrieval   # base indexée + poids : fixture + tableau
    uv run --project eval moi-electeur-eval report      # depuis la fixture, sans base

Définitions (rappel@k normalisé par min(k, |R|), succès@k, couverture) :
`eval/src/moi_electeur_eval/recall.py`.
