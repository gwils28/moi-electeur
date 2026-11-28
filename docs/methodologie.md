# Méthodologie

Moi Électeur aide à connaître le contenu des programmes officiels des candidats à une élection.
Il ne dit pas pour qui voter : aucun texte de l'application ne classe un candidat, l'ordre des
candidats est tiré au sort à chaque visite, et un mode aveugle masque noms, partis et couleurs.

Cette page décrit d'où viennent les données, comment elles sont calculées, comment l'ensemble a
été évalué, et ce qu'il faut savoir de ses limites. Le code, les données validées, les prompts et
les rapports d'évaluation sont publics dans le dépôt du projet.

## 1. Sources

- **Élection 2022** (présidentielle, premier tour, 12 candidats) : 24 documents officiels, deux
  par candidat (programme et profession de foi), archivés (Web Archive, site de la Commission
  nationale de contrôle de la campagne électorale) avec leur empreinte sha256.
- Les documents sont découpés en **794 extraits** d'environ une demi-page (300 à 600 unités de
  texte, ou tokens), avec leur page et leur document d'origine. Toute citation affichée renvoie à un de ces extraits.
- La version abrégée du programme d'un candidat (Jean-Luc Mélenchon) est la seule disponible
  dans le corpus : certaines de ses propositions détaillées peuvent manquer.

## 2. Affirmations et axes de la boussole

- **30 affirmations**, 5 par thème (économie, social, écologie, Europe et international,
  régalien et immigration, institutions). Rédigées avec l'aide d'un modèle de langage (Claude),
  puis **validées par le mainteneur** ; elles portent sur des mesures que les programmes peuvent
  trancher, et leur sens est alterné pour limiter le biais d'acquiescement.
- **Deux axes** : économie (de « Interventionnisme / Redistribution » à « Libéralisme / Baisse de
  la fiscalité ») ; société et souveraineté (de « Progressisme / Intégration européenne » à
  « Conservatisme / Autorité / Souverainisme »). Chaque affirmation est rattachée à un axe, avec
  un sens et un poids ; trois affirmations au classement discutable (nucléaire, VIe République,
  référendum d'initiative citoyenne) ont un poids réduit de moitié.
- Le choix des affirmations et des axes est un choix éditorial : il conditionne les résultats.

## 3. Positions des candidats

- Pour chaque candidat et chaque affirmation, les 6 extraits du programme les plus proches de
  l'affirmation sont soumis à un modèle de langage (Claude Sonnet 5.5) **sans le nom du
  candidat** ni le titre du document, qui propose une position : de -2 (s'engage contre) à +2
  (s'engage pour), ou **silence** si les extraits ne traitent pas le sujet, avec au moins une
  citation exacte. Chaque citation est retrouvée mot pour mot dans son extrait ; une position
  sans citation retrouvée est écartée.
- Les propositions de mesures phares et de chiffrages (comparateur) suivent le même principe ;
  un montant n'est retenu que s'il figure dans la citation du chiffrage.
- **Revue humaine** : chaque proposition devait être validée, corrigée ou rejetée par le
  mainteneur. **Pour 2022, les 360 positions et 343 mesures ont été validées en bloc, sans
  relecture individuelle** (chaque décision porte cette mention). Les positions affichées sont
  donc celles proposées par le modèle, filtrées par les vérifications automatiques ci-dessus.
- Sur 360 positions, 157 sont des silences : un programme ne se prononce pas sur toutes les
  affirmations.

## 4. Calculs

Tous les calculs de la boussole sont faits **dans votre navigateur** : vos réponses ne sont
envoyées nulle part.

- **Proximité** avec un candidat : 100 × (1 − Σ w·|u − c| / Σ w·4), sur les affirmations où vous
  et le candidat vous prononcez (u : votre réponse, c : la position du candidat, de -2 à +2 ;
  w : le poids que vous donnez au thème, de 1 à 3). Les « sans avis » et les silences sont
  exclus. La **couverture** indique sur combien de vos réponses la proximité est calculée :
  calculée sur peu d'affirmations, elle est moins fiable.
- **Projection sur l'échiquier (mode A)** : sur chaque axe, 10 × Σ w·sens·v / Σ w·2, où v est la
  position (la vôtre ou celle d'un candidat), sens et w ceux de l'affirmation ; les silences
  sont exclus.
- **Mode B (analyse en composantes principales)** : axes calculés à partir des positions des
  candidats ; la part de variance expliquée et les affirmations les plus contributives sont
  affichées.
- **Comparateur** : mesures phares par thème ; divergences = affirmations où deux programmes
  choisis s'écartent de 3 points ou plus ; radar = statut le plus précis des chiffrages du thème
  (chiffré, partiel, intention, ou silence si aucune mesure n'est retenue).
- **Positions** : tableau complet des affirmations × candidats, par thème : la position retenue
  pour chaque programme (-2 à +2, ou silence), sa confiance, une éventuelle correction à la revue
  et les passages cités. Mêmes données que la boussole, sans total ni classement.

## 5. Interrogatoire des programmes (chat)

- Votre question est comparée aux 794 extraits par une **recherche hybride** (sens des mots avec
  le modèle multilingual-e5-large, et mots exacts), qui retient les 4 extraits les plus proches
  **par candidat**.
- Un modèle de langage (Claude Haiku 5.5 en réponse rapide, Claude Sonnet 5.5 en réponse
  détaillée) résume ce que disent ces extraits, candidat par candidat, en ne désignant les
  candidats que par des jetons remplacés à l'affichage. Il a pour consigne de n'utiliser que les
  extraits, de citer chaque proposition, d'écrire « Aucune proposition recensée dans le
  programme officiel sur ce point » quand un candidat n'en parle pas, et de ne jamais orienter
  le vote.
- Chaque citation est vérifiée dans son extrait ; une citation non retrouvée est signalée. Les
  formulations qui pourraient classer un candidat sont repérées et signalées.
- Votre question est envoyée au serveur pour produire la réponse, **sans être enregistrée** ;
  les journaux ne contiennent ni la question, ni la réponse, ni votre adresse IP.

## 6. Évaluation (backtest 2022)

Le rapport complet est dans le dépôt (`eval/reports/2026-11-27.md`). Principaux résultats :

- **Recherche** (60 questions annotées) : en moyenne, 72 % des extraits pertinents attendus (au
  plus 4 par candidat) figurent parmi les 4 retenus ; pour 89 % des couples question et candidat,
  au moins un extrait pertinent est retenu.
- **Chat** (60 questions, deux modèles) : 99 % des citations retrouvées dans leur extrait ; 96 %
  des silences corrects ; 7 à 9 % de **faux silences** (un candidat qui traite le sujet déclaré
  silencieux, le plus souvent parce que le bon extrait n'a pas été retrouvé) ; refus d'orienter
  le vote dans 100 % des cas ; selon un second modèle chargé de vérifier les réponses, 1 à 2 %
  des affirmations ne sont pas appuyées par les passages cités, et un contrôle manuel de ces cas
  n'a trouvé aucune affirmation inventée.
- **Neutralité** : avec l'ordre des candidats tiré au sort plusieurs fois, la place d'un
  candidat dans la réponse n'a qu'un effet faible sur la longueur de sa section.
- **Positions** : l'ordre des candidats sur les deux axes concorde avec le jugement d'experts
  de la Chapel Hill Expert Survey sur leurs partis (corrélation de rangs de 0,83 à 0,90 sur les 8
  candidats dont le parti est couvert).

## 7. Limites et biais connus

- **Positions 2022 validées en bloc**, sans relecture individuelle : une erreur du modèle non
  détectée par les vérifications automatiques reste possible. Signalez-la.
- **Faux silences** : une proposition présente dans un programme peut ne pas être trouvée (par la
  boussole comme par le chat).
- **Couverture inégale** : certains programmes ne se prononcent que sur quelques affirmations
  (7 sur 30 pour deux candidats) ; leur proximité est alors calculée sur peu de réponses et
  peut paraître élevée. La couverture est affichée à côté de chaque proximité.
- **Choix éditoriaux** : affirmations, axes et poids conditionnent l'échiquier ; d'autres choix
  donneraient d'autres positions.
- **Modèles de langage** : les positions, les mesures et les réponses du chat sont produites par
  des modèles, contrôlées automatiquement mais pas infaillibles ; toutes les citations renvoient
  au document source, à vérifier en cas de doute.
- **Évaluation** : le jeu de questions a été annoté à l'aide d'agents (méthode publiée), et la
  comparaison avec la Chapel Hill Expert Survey ne porte que sur 8 candidats.

## 8. Confidentialité

Aucun cookie, aucun suivi, aucune ressource tierce. Les réponses au questionnaire restent dans
votre navigateur (un lien de partage les encode après `#`, partie jamais envoyée au serveur). Le
chat reçoit votre question sans l'enregistrer.

## 9. Code, données, licence

Code sous licence AGPL-3.0, données sous licence CC BY-SA 4.0. Dépôt public :
<https://github.com/gwils28/moi-electeur> (code, données validées, prompts, rapports
d'évaluation, notes d'implémentation). Pour signaler une erreur : ouvrir un ticket sur le dépôt.
