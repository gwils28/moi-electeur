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

## Chapel Hill Expert Survey : `ches-mapping-2022.json`

Corrélation de rangs (Spearman) entre les coordonnées du mode A et les scores des partis :
`lrecon` (gauche-droite économique) pour l'axe x, `galtan` (libertaire-autoritaire) pour l'axe y.
Le fichier de la CHES n'est pas versionné ici (téléchargement soumis à l'accord du mainteneur) :
le déposer sous `eval/reference/ches/`, puis vérifier les abréviations de
`ches-mapping-2022.json` (arthaud, lassalle et poutou n'ont pas de parti couvert ; Reconquête
n'existe que dans les vagues postérieures à 2021).
