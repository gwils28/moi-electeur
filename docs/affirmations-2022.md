# Affirmations de la boussole 2022 (M3a, validées)

Proposition de l'agent (D22, PLAN § 5.0), **validée sans correction par le mainteneur le 2026-11-27** et écrite dans `data/elections/fr-presidentielle-2022/statements.json` (source de vérité désormais : ce document n'est plus mis à jour).

**Règles** (SPEC § 4.2) : 25 à 35 affirmations, au moins 4 par thème et 10 par axe ; `sens` = +1 si « d'accord » pousse vers +10 sur l'axe, -1 sinon ; sens alternés pour limiter le biais d'acquiescement ; ordre groupé par thème (§ 15). Formulations neutres, sans adjectif appréciatif, portant sur une mesure que les programmes officiels peuvent trancher.

**Axes 2022** (`election_config.json`) :
- x (Économie) : -10 « Interventionnisme / Redistribution », +10 « Libéralisme / Baisse de la fiscalité » ;
- y (Société & souveraineté) : -10 « Progressisme / Intégration européenne », +10 « Conservatisme / Autorité / Souverainisme ».

**Bilan** : 30 affirmations, 5 par thème ; axe x : 12 (5 en +1, 7 en -1) ; axe y : 18 (10 en +1, 8 en -1). Poids 1 sauf trois cas discutables à 0,5.

| id | thème | affirmation | axe | sens | poids | remarque | ✅ / correction |
|---|---|---|---|---|---|---|---|
| s01 | economie | Il faut rétablir un impôt sur la fortune qui porte aussi sur le patrimoine financier. | x | -1 | 1 | | |
| s02 | economie | Les impôts de production payés par les entreprises doivent être fortement réduits. | x | +1 | 1 | | |
| s03 | economie | L'État doit nationaliser ou reprendre le contrôle d'entreprises stratégiques (énergie, autoroutes, banques). | x | -1 | 1 | | |
| s04 | economie | Le nombre de fonctionnaires doit être réduit pour diminuer la dépense publique. | x | +1 | 1 | | |
| s05 | economie | La réduction de la dette publique doit passer avant de nouvelles dépenses. | x | +1 | 1 | | |
| s06 | social | L'âge légal de départ à la retraite doit être ramené à 60 ans. | x | -1 | 1 | | |
| s07 | social | Le SMIC doit être augmenté au-delà des revalorisations automatiques. | x | -1 | 1 | | |
| s08 | social | Le versement du RSA ou des allocations chômage doit être davantage conditionné à une activité ou à la reprise d'un emploi. | x | +1 | 1 | | |
| s09 | social | Les loyers doivent être encadrés dans les zones où le logement est cher. | x | -1 | 1 | | |
| s10 | social | Le port d'un uniforme doit devenir obligatoire à l'école. | y | +1 | 1 | Thème social mais clivage d'autorité : placé sur y. | |
| s11 | ecologie | La France doit construire de nouveaux réacteurs nucléaires. | y | +1 | 0,5 | Discutable : le nucléaire traverse les deux camps de l'axe y (soutenu aussi par une partie de la gauche). Poids réduit ; alternative : retirer l'affirmation. | |
| s12 | ecologie | Les vols intérieurs doivent être supprimés lorsqu'une alternative en train de moins de quatre heures existe. | x | -1 | 1 | Régulation par l'État : placée sur x. | |
| s13 | ecologie | L'installation de nouvelles éoliennes doit être arrêtée. | y | +1 | 1 | Clivage progressisme / conservatisme (D23). | |
| s14 | ecologie | La transition écologique justifie de taxer davantage les activités les plus polluantes. | x | -1 | 1 | | |
| s15 | ecologie | Les normes environnementales imposées aux agriculteurs doivent être assouplies. | x | +1 | 1 | | |
| s16 | europe_international | La France doit quitter le commandement intégré de l'OTAN. | y | +1 | 1 | Souverainisme : rapproche des candidats de bords opposés sur x, c'est attendu sur cet axe. | |
| s17 | europe_international | Le droit français doit pouvoir primer sur le droit européen. | y | +1 | 1 | | |
| s18 | europe_international | L'Union européenne doit se doter d'une défense commune. | y | -1 | 1 | | |
| s19 | europe_international | La France doit soutenir de nouveaux accords de libre-échange négociés par l'Union européenne. | y | -1 | 1 | Discutable : le libre-échange relève aussi de l'économie (x). | |
| s20 | europe_international | Les décisions de l'Union européenne doivent davantage se prendre à la majorité qualifiée plutôt qu'à l'unanimité. | y | -1 | 1 | Risque de nombreux silences (sujet technique) : à confirmer après le pilote. | |
| s21 | regalien_immigration | Des peines minimales obligatoires doivent être instaurées pour les récidivistes. | y | +1 | 1 | | |
| s22 | regalien_immigration | Le nombre d'immigrés accueillis chaque année doit être fortement réduit. | y | +1 | 1 | | |
| s23 | regalien_immigration | Le droit du sol doit être supprimé. | y | +1 | 1 | | |
| s24 | regalien_immigration | Les travailleurs sans papiers qui occupent un emploi doivent pouvoir être régularisés. | y | -1 | 1 | | |
| s25 | regalien_immigration | La consommation de cannabis doit être légalisée et encadrée. | y | -1 | 1 | Silence de 6 candidats sur 12 d'après le jeu de fumée M2 : à garder (les silences sont exclus du calcul) ou à remplacer. | |
| s26 | institutions | Les étrangers non européens résidant en France doivent pouvoir voter aux élections locales. | y | -1 | 1 | | |
| s27 | institutions | Le référendum doit pouvoir porter sur l'immigration. | y | +1 | 1 | | |
| s28 | institutions | La Constitution doit être refondée par une assemblée constituante (VIe République). | y | -1 | 0,5 | Discutable : réforme institutionnelle plus que clivage progressisme / conservatisme. | |
| s29 | institutions | La Corse doit obtenir un statut d'autonomie. | y | -1 | 1 | Décentralisation contre centralisation (autorité) ; risque de silences. | |
| s30 | institutions | Il faut instaurer le référendum d'initiative citoyenne (RIC). | y | +1 | 0,5 | Discutable : soutenu de part et d'autre de l'axe y ; placé côté souveraineté populaire. Alternative : retirer. | |

**Écartées** (redondantes ou peu tranchées dans les programmes) : report de l'âge de la retraite au-delà de 62 ans (redondant avec s06), retraite par capitalisation, proportionnelle aux législatives (soutenue presque partout), encadrement de la police (peu de programmes précis).

**Suite** : `statements.json` écrit, `pipeline validate` vert, puis le pilote d'extraction (D28) dira si s20, s25 et s29 ont trop de silences.
