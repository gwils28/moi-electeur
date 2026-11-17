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
