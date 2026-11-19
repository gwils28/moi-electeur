# Sources du corpus : présidentielle 2022 (1er tour, 10 avril 2022)

> Statut : **validé** (PLAN D11, 2026-11-19 : règle, tableaux et points P1 à P8 acceptés). Recherche et vérification le 2026-11-19 : chaque URL d'archive a été ouverte, le PDF compté (pages, mots extraits) et, pour les professions de foi, comparé au fichier en ligne.
> Mode d'emploi : annoter sous `> 📝 Annotation :`. Une fois validée, chaque ligne « retenue » est ajoutée par `uv run pipeline add-source` (D12), qui calcule le sha256.

## Règle de sélection proposée

1. **Uniquement des documents du candidat, de son parti ou de l'État** (SPEC § 1). Copies tierces écartées (fhf.fr, macommune.info, atterres.org, etc.).
2. **Deux documents par candidat, pas plus** : la **profession de foi du 1er tour** et le **document que la campagne présentait comme « le programme »** (sa version la plus récente avant le 10/04/2022). Pas de livrets thématiques, de synthèses, de chiffrages ni de versions FALC en M2 : les ajouter pour certains candidats seulement déséquilibrerait le corpus. Ils pourront être ajoutés de façon uniforme plus tard, avec mesure de l'effet en M4.
3. **`source_url` = instantané Wayback brut (`id_/`)** pour tous les documents, même ceux encore en ligne : URL stable, sha256 reproductible, une seule méthode de téléchargement. L'URL d'origine reste notée ici et dans `program_url`.

Conséquence assumée : les volumes sont très inégaux (de ≈ 5 000 à ≈ 84 000 mots). La récupération par candidat (top-k par candidat, § 6.1) évite qu'un gros programme écrase les autres. En revanche, un programme court donne plus de réponses « Aucune proposition recensée », ce qui reflète fidèlement le document officiel. Ce point sera expliqué sur la page méthodologie.

> 📝 Annotation :

## Professions de foi (État : CNCCEP)

Source : https://www.cnccep.fr/candidats.html (Commission nationale de contrôle de la campagne électorale). Version générale, pas la version FALC. Les 12 fichiers sont encore en ligne et identiques à la capture du 28-29/03/2022, sauf Dupont-Aignan (voir P1). Le site du ministère (`programme-candidats.interieur.gouv.fr`) bloque les robots et n'est pas archivé de façon exploitable.

Préfixe d'archive : `https://web.archive.org/web/<horodatage>id_/https://www.cnccep.fr/pdfs/`

| Candidat | Fichier | Horodatage | Pages | Mots | Remarque |
|---|---|---|---|---|---|
| Nathalie Arthaud | `Candidat-01-Nathalie-Arthaud-Declaration.pdf` | 20220328220458 | 4 | ≈ 1 525 | |
| Nicolas Dupont-Aignan | `Candidat-02-Nicolas-Dupont-Aignan-Declaration-accessible.pdf` | 20220408213655 | 2 | ≈ 1 078 | version corrigée (P1) |
| Anne Hidalgo | `Candidat-03-Anne-Hidalgo-Declaration.pdf` | 20220328220437 | 4 | ≈ 1 961 | |
| Yannick Jadot | `Candidat-04-Yannick-Jadot-Declaration-accessible.pdf` | 20220328220436 | 4 | ≈ 1 067 | |
| Jean Lassalle | `Candidat-05-Jean-Lassalle-Declaration.pdf` | 20220328220512 | 2 | ≈ 1 324 | |
| Marine Le Pen | `Candidat-06-Marine-Le-Pen-Declaration-accessible.pdf` | 20220328220437 | 3 | ≈ 968 | page 1 en image (P6) |
| Emmanuel Macron | `Candidat-07-Emmanuel-Macron-Declaration.pdf` | 20220329144919 | 3 | ≈ 1 405 | |
| Jean-Luc Mélenchon | `Candidat-08-Jean-Luc-Melenchon-Declaration-accessible.pdf` | 20220328220532 | 4 | ≈ 1 414 | |
| Valérie Pécresse | `Candidat-09-Valerie-Pecresse-Declaration-accessible.pdf` | 20220328220502 | 4 | ≈ 1 450 | |
| Philippe Poutou | `Candidat-10-Philippe-Poutou-Declaration.pdf` | 20220328220443 | 4 | ≈ 1 348 | |
| Fabien Roussel | `Candidat-11-Fabien-Roussel-Declaration-accessible.pdf` | 20220328220449 | 3 | ≈ 1 250 | |
| Éric Zemmour | `Candidat-12-Eric-Zemmour-Declaration.pdf` | 20220328220458 | 4 | ≈ 1 711 | page 1 en image (P6) |

> 📝 Annotation :

## Programmes

| Candidat | Document retenu | Pages | Mots | URL d'archive (`source_url`) | URL d'origine | Points |
|---|---|---|---|---|---|---|
| Nathalie Arthaud | Brochure de campagne « Nathalie Arthaud candidate à l'élection présidentielle » (16/02/2022) | 36 | non compté | https://web.archive.org/web/20220304230512id_/https://www.nathalie-arthaud.info/sites/default/files/documents/brochure-janvier_2022_bd.pdf | même chemin sur nathalie-arthaud.info (hors ligne) ; copie LO en ligne | P4 |
| Nicolas Dupont-Aignan | « Programme général » (29/03/2022) | 209 | ≈ 84 100 | https://web.archive.org/web/20220401142413id_/https://2022nda.fr/wp-content/uploads/2022/03/Programme-general-1.pdf | 2022nda.fr (403) | P5 |
| Anne Hidalgo | Programme officiel, « 70 propositions », version A4 (25/02/2022) | 44 | ≈ 15 450 | https://web.archive.org/web/20220301150408id_/https://assets.nationbuilder.com/2022avechidalgo/pages/208/attachments/original/1645795527/Anne_Hidalgo_Programme_officiel_en_A4_l%C3%A9ger.pdf | lié depuis 2022avechidalgo.fr/notre_programme | |
| Yannick Jadot | « Programme des écologistes » (25/03/2022) | 131 | ≈ 38 700 | https://web.archive.org/web/20220327012752id_/https://assets.nationbuilder.com/themes/6181b6eb4445ea720389b314/attachments/original/1648232746/programme_des_ecologistes.pdf | lié depuis jadot2022.fr/programme (en ligne) | P2 |
| Jean Lassalle | « La France authentique », version A4 V5 (25/02/2022) | 12 | ≈ 5 080 | https://web.archive.org/web/20220314141131id_/https://jl2022.fr/wp-content/uploads/2022/03/Programme-A4-V5-25_02_22.pdf | jl2022.fr (en ligne) | |
| Marine Le Pen | Manifeste « M la France, programme présidentiel » (version du 29/03/2022) | 36 | ≈ 12 500 | https://web.archive.org/web/20220329165019id_/https://mlafrance.fr/pdfs/manifeste-m-la-france-programme-presidentiel.pdf | mlafrance.fr (en ligne, identique) | P3 |
| Emmanuel Macron | « Emmanuel Macron avec vous », programme 24 pages (16/03/2022) | 13 (planches doubles) | ≈ 6 400 | https://web.archive.org/web/20220317215226id_/https://avecvous.fr/wp-content/uploads/2022/03/Emmanuel-Macron-Avec-Vous-24-pages.pdf | avecvous.fr (URL morte) | P7, P8 |
| Jean-Luc Mélenchon | « L'Avenir en commun », programme en version abrégée (03/04/2022) | 32 | ≈ 5 200 | https://web.archive.org/web/20220410183816id_/https://melenchon2022.fr/wp-content/uploads/2022/04/LAvenir-en-commun-le-programme-en-version-abregee.pdf | melenchon2022.fr (redirige vers 2027) | P3 |
| Valérie Pécresse | « Le courage de faire », 16 pages (19/03/2022) | 16 | ≈ 4 980 | https://web.archive.org/web/20220324170011id_/https://valeriepecresse.fr/wp-content/uploads/2022/03/16P-VP2022-ok.pdf | valeriepecresse.fr (en ligne) | P2 |
| Philippe Poutou | Brochure programme Poutou 2022 (24/02/2022) | 32 | ≈ 8 475 | https://web.archive.org/web/20220401130549id_/https://poutou2022.org/sites/default/files/2022-02/brochure_programme_poutou_2022_2.pdf | lié depuis poutou2022.org/programme ; copie identique sur npa-lanticapitaliste.org | |
| Fabien Roussel | « La France des Jours heureux », livre-programme (19/01/2022) | 67 | ≈ 27 400 | https://web.archive.org/web/20220125104923id_/https://d3n8a8pro7vhmx.cloudfront.net/fabienroussel2022/pages/217/attachments/original/1643038967/exe_la_france_des_jours_heureux_LIVRE_stc.pdf | lié depuis fabienroussel2022.fr/le_programme | |
| Éric Zemmour | « Pour que la France reste la France. Mon programme » (25/03/2022) | 73 | ≈ 26 700 | https://web.archive.org/web/20220326170951id_/https://assets.nationbuilder.com/themes/61c071ce4764e8b1483d1a8c/attachments/original/1648220408/programme_eric_zemmour_presidentielle_2022.pdf | lié depuis programme.zemmour2022.fr | |

> 📝 Annotation :

## Points à trancher (avec proposition)

- **P1. Profession de foi de Dupont-Aignan** : deux versions (24/03 et 07/04, une coquille « LIBRE » corrigée en « LIBRES »). **Proposition : la version corrigée**, celle en ligne aujourd'hui.
- **P2. Plusieurs versions d'un même programme** : Jadot (programme 131 p. du 25/03 ou synthèse 39 p. du 02/02), Pécresse (10/03 ou 19/03, quasi identiques). **Proposition : le document présenté comme « le programme », dans sa version la plus récente** (Jadot 131 p., Pécresse 19/03).
- **P3. Le Pen et Mélenchon** (✅ option (a) validée le 2026-11-19) : publient l'essentiel de leur programme en livrets thématiques (≈ 18 pour Le Pen, ≈ 40 pour Mélenchon). Le programme intégral de Mélenchon est un livre (Seuil, 2021) sans PDF officiel. Son texte intégral existe en HTML sur laec.fr, lié depuis la page programme officielle, mais il s'agit d'un site d'appui militant. Options :
  - (a) **Proposition : appliquer la règle sans exception** (manifeste 36 p. pour Le Pen, version abrégée 32 p. pour Mélenchon) et documenter la limite ; ajout uniforme des livrets plus tard, mesuré en M4 ;
  - (b) ajouter les livrets de ces deux candidats seulement (corpus plus fidèle mais règle à deux vitesses) ;
  - (c) retenir laec.fr pour Mélenchon (captures 2022), si tu considères qu'il émane de la campagne.
- **P4. Arthaud** (✅ validé le 2026-11-19) : Lutte ouvrière revendique « un programme de luttes » et non un programme électoral classique. **Proposition : la brochure de campagne de 36 p.**, document le plus complet publié par la candidate. D'autres brochures (11/2021, 02/2022) n'ont pas été examinées.
- **P5. Dupont-Aignan** (✅ validé le 2026-11-19) : « Programme général » de 209 p., en deux versions quasi identiques (11/03 et 29/03), disponible seulement dans la Wayback. **Proposition : version du 29/03.** C'est de loin le plus gros document du corpus (≈ 84 000 mots, 13 fois Macron) : voir la conséquence assumée de la règle.
- **P6. Pages en image** : la page 1 des professions de foi de Le Pen et Zemmour (et la couverture de quelques autres) n'a pas de couche texte. Ce sont des couvertures (photo, slogan), le reste est extractible. **Proposition : pas d'OCR**, les pages vides sont simplement signalées par `extract` (D20 : seul un PDF sans aucun texte serait exclu).
- **P7. Macron** : le PDF « 24 pages » est en planches doubles (13 pages PDF pour 24 pages imprimées). **Proposition : citer le numéro de page PDF** (celui qu'un lecteur voit dans son lecteur PDF), règle valable pour tout le corpus.
- **P8. Macron** : le projet détaillé existait aussi en HTML sur avecvous.fr (non vérifié). **Proposition : s'en tenir au PDF** (règle 2).

> 📝 Annotation :

## Écartés ou pour plus tard

- Versions FALC (CNCCEP et campagnes), synthèses (« 22 mesures » Le Pen, « 100 décisions » Dupont-Aignan, synthèse 8 p. Roussel, synthèse 8 p. Macron, synthèse Jadot), chiffrages (Dupont-Aignan, Le Pen), livrets thématiques (Le Pen, Mélenchon, Zemmour non recherchés) : hors règle 2.
- `AEC-novembre-2020.pdf` (Mélenchon) : version antérieure au programme 2022.
- Copies de la profession de foi sur les sites de campagne : doublons de la source CNCCEP.
- Pages HTML de programme (Arthaud « Mon programme de luttes », Dupont-Aignan « Le projet », Mélenchon page programme) : doublons ou résumés des PDF retenus.
