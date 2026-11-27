# Revue humaine des propositions (M3c)

Les positions et mesures proposées par Claude (`pipeline propose-positions`, `propose-measures`)
sont écrites au statut `pending`. Le front n'en charge aucune tant qu'elles ne sont pas
**validées** ou **corrigées**, et la boussole 2022 n'est publiée qu'une fois **toutes** les
positions revues (`compass_ready()`).

## Lancer

```sh
uv run pipeline review data/elections/fr-presidentielle-2022          # avancement
uv run --project notebooks marimo run review/review_positions.py      # positions
uv run --project notebooks marimo run review/review_measures.py       # mesures
```

Les applications tournent en local (aucune surface en production). Le texte des extraits vient de
`data/elections/<id>/sources/chunks.jsonl` (ignoré par git, produit par `pipeline chunk`) ; sans
lui, seules les citations s'affichent. Autre élection : `MOI_ELECTEUR_ELECTION=<dossier>`.
Nom inscrit dans `review.reviewer` : `MOI_ELECTEUR_REVIEWER` (défaut : `mainteneur`, pour ne pas
publier de nom).

## Décider

- **Valider** : la proposition est juste telle quelle.
- **Corriger** : choisir la valeur (de +2 à -2, ou silence), éventuellement la confiance, et, si
  les citations ne conviennent pas, en saisir d'autres (une par ligne, recopiées du programme :
  chacune doit figurer dans un extrait de ce candidat, elle est enregistrée telle qu'elle y
  figure). La valeur d'origine est conservée dans `proposed_value`. Pour une mesure : titre,
  résumé ou chiffrage ; les originaux des champs modifiés vont dans `proposed`.
- **Rejeter** : la proposition est hors sujet ou inexploitable ; elle n'est pas chargée.
- Note facultative dans chaque cas.

Chaque décision est écrite aussitôt, puis toute l'élection est revalidée (schémas et contrôles
croisés) : une décision invalide (valeur sans citation, citation introuvable) est refusée avec
un message et rien n'est modifié. On peut revenir sur une décision (case « Inclure … déjà
revues »). La file présente d'abord les propositions signalées : valeur refusée faute de
citation, citation non retrouvée, confiance faible ; pour les mesures, les groupes signalés puis
les chiffrages. La case « Masquer le nom du candidat » affiche l'alias du mode aveugle.

Repères pour l'échelle (prompt `prompts/positions_system.md`) : ±2 engagement explicite sur la
mesure ou son rejet ; ±1 orientation nette sans engagement précis ; 0 position explicitement
intermédiaire ; silence si les extraits ne traitent pas le sujet. Un silence peut venir de la
recherche (6 extraits par couple) : ouvrir les extraits, et le PDF en cas de doute.
