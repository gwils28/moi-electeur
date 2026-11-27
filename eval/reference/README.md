# Références externes du backtest (M4, PLAN D42)

## Codage manuel de référence : `codage-2022.csv`

60 couples (candidat, affirmation) tirés au sort, 5 par candidat, silences et valeurs mêlés
(`moi_electeur_eval.reference.sample_positions`, graine 7). **La valeur publiée n'y figure pas** :
coder chaque couple en lisant les programmes (colonne `sources`), sans regarder la boussole.

Colonne `code` : `2`, `1`, `0`, `-1`, `-2` ou `silence`, selon l'échelle du prompt d'extraction
(`prompts/positions_system.md`) :

- `2` / `-2` : le programme s'engage explicitement sur la mesure de l'affirmation, ou contre ;
- `1` / `-1` : il va nettement dans ce sens, ou dans le sens contraire, sans engagement précis ;
- `0` : position explicitement intermédiaire sur ce sujet précis (rare) ;
- `silence` : le programme ne traite pas le sujet.

Colonne `note` : facultative (passage, page, hésitation). Une ligne laissée vide n'est pas comptée.
Mesure : accord silence / non-silence, accord exact et à un cran près, kappa pondéré quadratique
(`moi_electeur_eval.reference.agreement`), dans le rapport du backtest.

## Chapel Hill Expert Survey : `ches-france.json`

Scores des partis français (vagues 2019 et 2024 : `lrecon`, gauche-droite économique ; `galtan`,
libertaire-autoritaire), extraits du fichier de tendance 1999-2024 de la CHES (source, date et
citation dans le fichier), avec le parti de rattachement de chaque candidat pour chaque vague.
Le fichier complet téléchargé (`ches/`) n'est pas versionné. Corrélation de rangs (Spearman)
avec les coordonnées du mode A : `moi_electeur_eval.reference.ches_correlation`, dans le rapport.
arthaud, lassalle et poutou n'ont de parti couvert dans aucune vague ; Reconquête (zemmour)
n'apparaît qu'en 2024, DLF (dupont-aignan) qu'en 2019.
