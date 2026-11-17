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
