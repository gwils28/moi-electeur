# Notes d'implémentation

Écarts par rapport au plan et choix conservateurs, par date.

## 2026-11-17 : M0 (socle)

Écarts au plan :
- **Fichiers de données enveloppés** : `statements.json`, `positions.json`, `measures.json` sont des objets `{ "election_id", "<liste>" }` et non des tableaux nus (SPEC § 4.2-4.4 montrait des éléments isolés). Permet de vérifier l'appartenance à l'élection.
- **Statut de revue `pending`** ajouté à `validated|corrected|rejected` : nécessaire pour les propositions LLM pas encore revues (M3). `reviewer` et `date` deviennent obligatoires dès qu'un statut de décision est posé.
- **Mesures** : champ `id` (`m001`) ajouté pour pouvoir les référencer depuis le comparateur.
- **Thèmes** : uniquement des objets `{id, label}` (l'exemple SPEC § 4.1 mêlait objets et chaînes).
- **Notebooks** : nommés `m0-01-donnees-demo.py` (tirets) comme prévu ; exécutés par pytest (`notebooks/tests`).
- **Hook de tests** `.claude/hooks/run-tests.sh` : ajout du dossier `notebooks` à la boucle pytest.
- **TypeScript 6.0** et non 7.0 : `typescript-eslint` 8.73 ne supporte pas encore TS ≥ 6.1.
- **Types TS générés** sans tuples pour `minItems/maxItems` (`ignoreMinAndMaxItems`) : bornes contrôlées à la validation.
- **Lint Python** : `E501` ignoré (longueur gérée par `ruff format`), `.claude/` exclu de ruff (hook non modifié).
- **Prettier** : `data/` exclu (fichiers écrits par `pipeline make-demo`, dont la vérification compare le contenu JSON, pas la mise en forme).

Choix conservateurs :
- Positions de démo **dérivées d'un profil latent + bruit seedé** (expliqué dans `notebooks/m0-01-donnees-demo.py`) ; le profil n'est jamais exposé.
- Une position est exigée pour **chaque** couple (candidat, affirmation), y compris les rejetées : la complétude de la revue est ainsi vérifiable.
- Une position retenue (`validated`/`corrected`) non nulle doit avoir au moins une citation.
- Image web : `next start` lancé directement (sans pnpm) sous l'utilisateur `node` ; ports Compose liés à `127.0.0.1`.

Suites de la relecture M0 :
- Un couple (candidat, affirmation) dont la seule position est `pending` ou `rejected` sera traité par le moteur comme un **silence** (exclu du calcul, signalé). À tester en M1.
- Citations : hors élection fictive, `evidence.document_title` doit appartenir au corpus du candidat (la démo n'a pas de corpus).
- Le contrôle des mots qui classent couvre aussi `services/rag/src` ; les exceptions marquées sont affichées en CI.

## 2026-11-17 : M1 (moteur, tests d'abord)

- **Correctif M0** : la règle ESLint `no-restricted-imports` du moteur (motif `group` avec négations) bloquait aussi les imports relatifs ; remplacée par une regex `^(?!\.{1,2}/)`. Vérifié : `lodash` refusé, `./types` accepté.
- `no-unused-vars` ignore les paramètres préfixés `_` (stubs « non implémenté » de la phase test d'abord).
- Fixture ACP partagée `schemas/fixtures/pca_toy.json` (calculable à la main), utilisée par Vitest, puis par pytest et le notebook m1-03.
- Code `#r=` : une lettre par affirmation (`a`..`e` pour -2..+2, `n` pour sans avis), puis `.`, puis un chiffre 1-3 par thème ; préfixe de version `1`.
- Valeurs hors [-2, 2] ou non entières, poids non strictement positifs : `RangeError` (entrée corrompue, jamais silencieusement corrigée).
- Le point d'arrêt « tests rouges à relire » est abandonné à la demande du mainteneur (le hook de tests bloque de toute façon un tour qui finit en rouge). Commits `test(...)` et `feat(...)` restent séparés.
- **Référence Python** du moteur (`pipeline/.../engine_ref.py`) et fixture `schemas/fixtures/engine_cases.json` générée par `pipeline engine-fixtures` : le moteur TS doit la reproduire à 1e-9 (`cross-python.test.ts`), la CI vérifie l'absence de dérive.
- `pipeline build` : JSON compacts dans `apps/web/public/data/<id>/` + `pca_model.json` + `manifest.json` ; lancé par `predev`/`prebuild` du web ; l'image Docker web a une étape Python dédiée.
- `codegen` : seuls `schemas/*.schema.json` sont passés à datamodel-codegen (le dossier `fixtures/` était lu comme un schéma).
- Mode B : le filtre par thème est désactivé (le modèle ACP est global) ; l'interface l'indique.
- Les données sont lues **au build** par le composant serveur et embarquées dans la page statique : aucune requête de données côté client (vérifié par Playwright : zéro requête pendant le parcours).
- Sans avis et non répondu sont équivalents pour le calcul (tous deux `null`).
- Ordre des candidats : tiré après montage (`useEffect`) pour éviter un écart d'hydratation serveur/client ; mêmes formes de marqueur en mode aveugle et normal (forme liée à l'index de config, pas à l'identité affichée).
- Règle ESLint dans `apps/web/src/components` : accès direct à `name`, `party`, `color`, `photo`, `blind_alias`, `document_title` interdit hors `CandidateDisplay`.
- Écart au plan : pas de tests Testing Library des composants ; la couverture des composants est assurée par Playwright (parcours complet, clavier, axe, mode aveugle). Tests unitaires Vitest sur `assembleElection` et `displayCandidate`.
- Test modifié : `apps/web/test/i18n.test.ts` (M0) adapté car `fr` contient désormais des objets et fonctions ; il vérifie toujours que toutes les chaînes sont non vides.
- Échiquier : `role="group"` au lieu de `role="img"` (axe : `nested-interactive`, les points sont des boutons).
- Suites de la relecture M1 : en mode aveugle, **forme et alias sont attribués selon le rang tiré au sort** (et non l'ordre public de `election_config.json`, qui rendait le mode aveugle réversible) ; les **citations sont masquées** (elles peuvent contenir un nom ou un slogan) ; test e2e sur les couleurs et sur la variation des alias entre sessions.
- ACP, orientation D3 : un candidat sans coordonnée mode A sur un axe compte comme 0 (centre) dans la corrélation. Choix conservateur, à surveiller avec peu de candidats.

## 2026-11-19 : M2 (plan détaillé)

- PLAN v0.3 : M2 détaillé, décisions D11 à D21 acceptées par le mainteneur.
- SPEC § 4.5 modifiée (D14) : les embeddings quittent la table `chunks` pour `chunk_embeddings(chunk_id, model, embedding vector(1024))`, afin de comparer bge-m3 et multilingual-e5-large en M4 sans réindexer le texte.
- Écart assumé à SPEC § 8.3 (D16) : thème des chunks par similarité d'embedding, sans arbitrage LLM en M2 ; l'arbitrage est reporté et mesuré en M4.

## 2026-11-19 : M2a (corpus 2022 et ingestion)

- **Écart au plan (D21)** : `index` et `db-migrate` passent dans M2b avec les modèles d'embedding dont ils dépendent. M2a couvre `add-source`, `fetch`, `extract`, `chunk` et le corpus 2022.
- `schemas/chunk.schema.json` créé (source unique du type « extrait », servira aux types TS du chat en M2c) ; ajout de `document_sha256` et `page_end` par rapport à SPEC § 4.5. Champ facultatif `description` ajouté aux thèmes (D16).
- `validate` (D13) : sans `statements`, `positions` ni `measures`, l'élection est « corpus seul » ; dès qu'un des trois existe, `statements` et `positions` redeviennent obligatoires. Nouveaux contrôles du corpus : URL, sha256 et chemin local uniques, chemin sous `sources/`. `build` ignore une élection « corpus seul » (message `IGNORÉ`).
- `add-source` / `fetch` : client HTTP générique (`moi-electeur-pipeline/0.1`, aucune information personnelle), 3 reprises sur 429/5xx, refus d'un contenu qui n'est pas un PDF (la Wayback renvoie parfois une page d'erreur en 200), refus d'un document déjà présent (URL ou sha256). `fetch` échoue si le fichier local est altéré ou si le document distant a changé.
- `extract` : PyMuPDF (licence AGPL, compatible avec celle du projet). Titre = bloc d'au plus 3 lignes et 150 caractères dont la police fait au moins 1,2 fois celle du corps (taille la plus fréquente pondérée par les caractères). Retirés : numéros de page, blocs sans lettre ni chiffre (ornements), blocs courts répétés sur plus de la moitié des pages (documents de 6 pages et plus, donc jamais les professions de foi), titres dupliqués consécutifs. Corrections observées sur le corpus réel : puces d'une police de puces (ZapfDingbats ou Wingdings, caractère isolé lu « n » chez Zemmour) remplacées par « • », la police Symbol restant intacte (€, ≥…) ; points de conduite de sommaire supprimés (Mélenchon) ; une ligne finissant par « lettre- » suivie d'une minuscule est recollée **en gardant le tiret** (« renonce-ment », « porte-parole ») : césure et mot composé sont indiscernables, garder le tiret ne perd rien du texte officiel (choix conservateur après relecture). Sortie interne `sources/extracted/<sha12>.json` (format privé au pipeline, non exposé, donc sans schéma).
- `chunk` : unités = titres et phrases, coupées en fenêtres de mots au-delà de `max/4` tokens ; cela garantit que tout extrait sauf le dernier d'un document fait au moins `min` tokens (contrainte `min <= 3/4 max` vérifiée). Recouvrement par phrases entières (50 tokens au plus) seulement après une coupure par la taille. Titres consécutifs fusionnés en un seul titre de section (200 caractères au plus, `maxLength` du schéma). `token_count` = recomptage du texte final par le tokenizer (peut différer de quelques tokens de la somme des unités).
- Tokenizer `FacebookAI/xlm-roberta-base` téléchargé anonymement depuis le Hub Hugging Face au premier `chunk` (mis en cache ensuite). Les tests utilisent un compteur « un mot = un token », jamais le réseau.
- **Version du corpus** : empreinte des sha256, des paramètres, du tokenizer **et du contenu des extraits** (texte et toutes les métadonnées). Sans le contenu, une évolution du code d'extraction laissait la version inchangée, ce qui aurait rendu le cache du chat (§ 6.2 bis) incohérent.
- `fr-presidentielle-2022/election_config.json` : couleurs tirées d'une palette qualitative neutre (Paul Tol), attribuées dans l'ordre alphabétique des noms, sans lien avec les couleurs des partis ; alias `Candidat·e A` à `L` (redistribués au hasard par le front, décision M1). `program_url` = URL d'origine du programme ou de la page programme.
- Résultat sur le corpus réel : 24 documents, sha256 vérifiés, aucun exclu ; pages sans texte (couvertures) : Le Pen PF p. 1 et 3, Zemmour PF p. 1, et quelques pages d'images dans les programmes. 801 extraits (médiane 568 tokens, max 600, 13 sous 300 : derniers extraits de documents) ; de 21 (Lassalle) à 251 (Dupont-Aignan) par candidat.
- mypy : `untyped_calls_exclude = ["pymupdf"]` (signatures PyMuPDF incomplètes).
- Correctif hors périmètre : `scripts/check-forbidden-words.py` plantait sur les `.pyc` de `services/rag/src/__pycache__` (présents localement, pas en CI) ; ils sont ignorés, test ajouté.
- Tests modifiés : `test_cli.py` (fetch, extract, chunk ne sont plus « non implémentés ») ; `test_extract.py` adapté pendant l'implémentation (rapport indexé par « candidat : titre », un titre étant commun aux 12 professions de foi).
- Suites de la relecture M2a (aucun point bloquant) : `extract` vérifie le chemin et le sha256 de chaque fichier avant extraction (le texte indexé est bien celui du document référencé) ; contrôle `local_path` sous `sources/` partagé par `validate`, `fetch` et `extract` (`local_path_issue`) ; `chunk` reprend candidat, titre et URL de la config courante, pas de l'extraction ; écriture atomique des téléchargements (`.part` puis renommage) ; `add-source` refuse un type inconnu et une URL non HTTP(S) avant tout téléchargement. Non traités (remarques) : blocs purement numériques retirés (perte possible d'un chiffre d'infographie isolé, sans libellé de toute façon), recouvrement absent quand la dernière phrase dépasse 50 tokens (conforme à « au plus »), compteur non additif non testé (seul le vrai tokenizer l'est, à la main).
