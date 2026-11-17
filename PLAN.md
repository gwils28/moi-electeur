# PLAN de Moi Électeur

> Statut : **v0.2, validé** (2026-11-17, décisions D1 à D10 acceptées, ajout du § 1 bis sur les notebooks R&D). Dérivé de [SPEC.md](SPEC.md) v0.2.
> Mode d'emploi : annoter directement sous les blocs `> 📝 Annotation :` (ou n'importe où). Rien n'est implémenté avant ton retour.
> Niveau de détail : M0 et M1 détaillés (prochaines étapes), M2 à M6 en grandes lignes, détaillés au moment venu.

## 0. Décisions à trancher avant de coder

Mes propositions par défaut sont en gras. Un simple « OK » suffit, sinon corrige.

| # | Sujet | Proposition | Alternative |
|---|---|---|---|
| D1 | Emplacement du moteur | **`packages/engine` uniquement** ; supprimer `apps/web/src/lib/engine` de l'arborescence SPEC § 13 et corriger `CLAUDE.md` (« Aucun appel réseau dans `packages/engine` ») | Garder les deux (incohérence actuelle SPEC § 13 / § 15.5) |
| D2 | Poids des thèmes et projection | **Les poids ×1/×2/×3 n'affectent que la proximité**. La projection (x, y) n'utilise que `weight_in_axis`, sinon la formule ne serait plus identique entre utilisateur et candidats | Appliquer aussi les poids utilisateur aux candidats lors de la projection (les points candidats bougeraient avec les poids de l'utilisateur) |
| D3 | Signe des axes ACP (mode B) | **Orienter chaque composante pour qu'elle corrèle positivement avec l'axe correspondant du mode A** (signe seulement, pas de rotation) : lecture cohérente entre modes | Convention arbitraire (plus forte charge positive) |
| D4 | Utilisateur hors bornes en mode B | **Rescale fixé par les candidats (max \|coord\| candidat = 9), utilisateur borné à [-10, 10]** et signalé s'il est borné | Rescale incluant l'utilisateur (les candidats bougent selon l'utilisateur, à éviter) |
| D5 | JSON statiques servis au front | **Générés par `pipeline build`, non commités** (`apps/web/public/data/` ignoré par git) ; la source versionnée reste `data/elections/` | Commiter la sortie de build (diffs plus lisibles, mais doublon) |
| D6 | Types générés depuis `schemas/` | **Générés et commités** (`packages/schemas-ts`, `pipeline/.../generated/`), la CI vérifie l'absence de dérive | Générés à la volée, non commités |
| D7 | Outillage qualité | **TS : ESLint (flat config) + Prettier ; Python : ruff + mypy** | Biome (TS) ; pyright (Python) |
| D8 | Version Python | **3.12 épinglée via `uv`** (`.python-version`) : compatibilité sûre des libs d'embedding (torch) ; la machine a 3.14 mais uv télécharge 3.12 | 3.13 |
| D9 | Élection de démo (M0/M1) | **`demo-fictive`** : 6 candidats fictifs (noms inventés, explicitement signalés « fictif »), 30 affirmations conformes aux règles de couverture | Attendre M2 et travailler directement sur 2022 |
| D10 | Nommage des branches | **Une branche par jalon ou sous-lot** (`feat/m0-socle`, `feat/m1-engine`…), PR vers `main`, tu commites et merges | Tout sur une branche |

> 📝 Annotation : OK

## 1. Principes transverses (valables pour tous les jalons)

- **Garde-fou « zéro I/O » du moteur** vérifié mécaniquement, pas seulement par convention : `packages/engine/package.json` sans `dependencies`, règle ESLint `no-restricted-globals` (`fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `navigator`, `localStorage`, `console`) et `no-restricted-imports` (tout module hors du package), plus un test qui parcourt les sources du package et échoue sur ces identifiants.
- **Filtrage `validated` / `corrected`** appliqué deux fois : à la génération (`pipeline build` exclut le reste) et au chargement côté front (loader qui rejette tout statut autre, test dédié).
- **Ordre des candidats** : un seul utilitaire `shuffleCandidates(ids, seed)` (dans le moteur, graine fournie par l'appelant), graine tirée une fois par session (`crypto.getRandomValues`, non persistée). Aucun `sort` par nom ou par score dans l'UI sauf le tableau accessible, trié sur demande explicite de l'utilisateur.
- **Pas de texte qui classe** : liste de mots interdits (`meilleur`, `plus crédible`, `gagnant`, `recommand`…) vérifiée par un test sur les chaînes UI (`apps/web/src/i18n/fr.ts`) et sur `prompts/`.
- **Contrôle du tiret cadratin en CI** : réutiliser la logique de `.claude/hooks/no-em-dash.py` dans un script `scripts/check-no-em-dash.py` exécuté par la CI (le hook ne protège que les sessions Claude Code).
- Chaque jalon se termine par : tests verts (sortie fournie), passage de l'agent `relecteur` sur le diff, mise à jour de `docs/notes-implementation.md`, message Conventional Commits proposé.

> 📝 Annotation : OK

## 1 bis. Notebooks R&D (traçabilité pédagogique)

Demande du mainteneur (2026-11-17) : toute phase de conception du **moteur**, de l'**intelligence** (RAG, prompts, extraction LLM) et de l'**analytique** (ACP, backtest) fait l'objet d'un notebook expliquant l'approche de façon pédagogique, structurée et traçable, pour des pairs Data Scientist / AI Engineer.

- **Outil : [marimo](https://marimo.io)** (notebooks en fichiers `.py` purs) plutôt que Jupyter : diffs lisibles en revue, pas de sortie binaire commitée, exécution réactive donc pas d'état caché, exécutables en script par la CI (`marimo export` / `python notebook.py`). Membre `notebooks` du workspace uv.
- **Emplacement** : `notebooks/<jalon>-<nn>-<sujet>.py` (ex. `m1-01-proximite.py`), index dans `notebooks/README.md`.
- **Structure imposée** (gabarit `notebooks/_template.py`) : 1. Question et contexte (lien SPEC) ; 2. Hypothèses et alternatives envisagées ; 3. Formalisation (formules) ; 4. Expérimentation sur données (démo ou 2022), figures ; 5. Résultats et limites ; 6. Décision prise et lien vers le code / la note d'implémentation ; métadonnées (date, auteur, versions des données, du modèle, du prompt, graine).
- **Traçabilité** : graines fixées, données lues depuis `data/` ou fixtures versionnées, aucun appel LLM réel en CI (réponses enregistrées dans `notebooks/fixtures/` quand nécessaire, coût annoncé avant tout run réel).
- **Cohérence avec le code** : pour le moteur (TS), le notebook contient une implémentation de référence Python des formules, comparée aux mêmes fixtures que les tests Vitest (`schemas/fixtures/`) ; un écart fait échouer la CI.
- **CI** : job `notebooks` qui exécute chaque notebook de bout en bout.

Notebooks prévus par jalon :
| Jalon | Notebooks |
|---|---|
| M0 | gabarit + `m0-01-donnees-demo.py` (construction et contrôle de couverture des données fictives) |
| M1 | `m1-01-proximite.py` (Manhattan pondérée, propriétés, choix D2), `m1-02-projection-a.py`, `m1-03-acp-mode-b.py` (ACP, signe D3, rescale D4) |
| M2 | découpage en chunks, comparaison des embeddings, retrieval hybride et RRF, prompt de neutralité |
| M3 | extraction des positions et mesures par LLM, analyse des corrections humaines |
| M4 | un notebook par dimension du backtest, alimentant le rapport |

> 📝 Annotation :

## 2. M0 : Socle

Objectif : un dépôt où `pnpm install && pnpm check` et `uv sync && uv run pytest` passent, `docker compose up` démarre les trois services, et les données de démo sont validées par les schémas. **Aucun coût LLM.**

### 2.1 Monorepo JS (pnpm)
- `package.json` racine (scripts : `lint`, `typecheck`, `test`, `check` = les trois + validation données + em-dash), `pnpm-workspace.yaml` (`apps/*`, `packages/*`), `tsconfig.base.json` (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`), `.nvmrc` (Node 24), `packageManager` épinglé.
- `packages/engine` : squelette vide + Vitest + config ESLint restrictive (§ 1). Le contenu arrive en M1.
- `packages/schemas-ts` : types TS générés depuis `schemas/` (`json-schema-to-typescript`), script `pnpm gen:types`.
- `apps/web` : Next.js (App Router, TS strict, Tailwind), page d'accueil minimale, `transpilePackages: ["@moi-electeur/engine"]`, polices auto-hébergées, aucun script tiers. Vitest + Playwright installés (un test fumée chacun).

### 2.2 Workspace Python (uv)
- `pyproject.toml` racine en workspace uv, membres `pipeline`, `services/rag`, `eval` (chacun son `pyproject.toml`, compatible avec `.claude/hooks/run-tests.sh`), `uv.lock` unique.
- `pipeline` : CLI (`typer`) avec la sous-commande `validate` (M0) ; les autres (`fetch`, `extract`…) en stubs qui échouent explicitement « non implémenté ».
- Modèles Pydantic générés depuis `schemas/` (`datamodel-code-generator`), script `uv run pipeline gen-models`.
- `services/rag` : FastAPI avec `/health` seulement.
- `eval` : squelette vide + pytest.

### 2.3 Schémas JSON (`schemas/`, draft 2020-12)
`election_config`, `statement`, `statements`, `position`, `positions`, `measure`, `measures`, `review` (sous-schéma partagé), `evidence` (partagé), `pca_model` (chargements + variance expliquée + facteurs de rescale), `manifest` (sortie de build : version du corpus, date, hash des fichiers).

Contrôles non exprimables en JSON Schema, codés dans `pipeline validate` :
- références croisées (`candidate_id`, `statement_id`, `theme` existent) ;
- couverture : 25 à 35 affirmations, ≥ 4 par thème, ≥ 10 par axe, sens (`direction`) mélangés sur chaque axe ;
- une position par couple (candidat, affirmation) ;
- `blind_alias` uniques et ne contenant pas le nom ;
- aucun champ `x`, `y` saisi dans les données candidats.

### 2.4 Données de démo (`data/elections/demo-fictive/`)
Config, 30 affirmations, positions des 6 candidats fictifs (statut `validated`, `reviewer: "demo"`), quelques mesures, et volontairement : 2 positions `rejected` et 1 `null` (pour tester filtrage et silences). Licence CC BY-SA 4.0 indiquée dans un `README` du dossier.

### 2.5 Docker Compose (dev)
`docker-compose.yml` : `db` (`pgvector/pgvector:pg16`, volume nommé, healthcheck), `rag` (Python 3.12 slim, `/health`), `web` (Node 24, `next dev`). `.env.example` (sans secret). La prod (`caddy`, `docker-compose.prod.yml`) est en M5.

### 2.6 CI GitHub Actions (`.github/workflows/ci.yml`)
Jobs : `js` (install, lint, typecheck, test), `python` (uv sync, ruff, mypy, pytest), `data` (`pipeline validate` sur toutes les élections, dérive des types générés), `hygiene` (em-dash, mots interdits). Playwright et axe-core ajoutés en M1.

### 2.6 bis Notebooks
Membre uv `notebooks` (marimo, numpy, pandas, matplotlib), gabarit, `m0-01-donnees-demo.py`, job CI d'exécution.

### 2.7 Documentation
- `CLAUDE.md` : remplir la section « Commandes » ; corriger le chemin du moteur (D1).
- `SPEC.md` § 13 : corriger l'arborescence (D1).
- `README.md` : démarrage rapide.

### 2.8 Critères d'acceptation M0
- [ ] `pnpm check` vert ; `uv run pytest` vert (sorties collées dans la PR).
- [ ] `docker compose up -d` : `db` healthy, `curl localhost:8000/health` → 200, `localhost:3000` répond.
- [ ] `uv run pipeline validate data/elections/demo-fictive` vert ; un fichier volontairement cassé est rejeté (test).
- [ ] Le test « zéro I/O » échoue si on ajoute `fetch` dans `packages/engine` (vérifié puis retiré).
- [ ] CI verte sur la PR.

> 📝 Annotation : ok

## 3. M1 : Moteur + boussole complète (100 % client)

Objectif : parcours questionnaire → résultats → échiquier → panneau, mode aveugle, « Et si », sur `demo-fictive`. **Aucun coût LLM, aucun appel réseau hors chargement des JSON statiques.**

### 3.1 Moteur (`packages/engine`), test d'abord
Ordre : j'écris d'abord **tous les tests** (unitaires + propriétés `fast-check`), je te les montre (commit proposé séparé `test(engine): …`), puis l'implémentation.

API envisagée (fonctions pures, entrées immuables) :

| Fonction | Rôle |
|---|---|
| `proximity(user, candidate, statements, themeWeights)` | → `{ score: 0..100, coverage: 0..1, n, lowCoverage }` (SPEC § 5.2) ; `null` si S vide |
| `projectA(values, statements)` | → `{ x, y }` dans [-10, 10], coordonnée `null` si aucune affirmation de l'axe n'a de valeur (SPEC § 5.3) |
| `projectB(values, pcaModel)` | → `{ x, y, clamped }` (silences imputés à 0, centrage, chargements, rescale, D4) |
| `compare(user, candidate, statements)` | → accords (\|écart\| ≤ 1), désaccords (≥ 3), silences |
| `filterByTheme(statements, themeId)` | sous-ensemble pour le filtre thématique |
| `shuffleCandidates(ids, seed)` | permutation déterministe (PRNG seedé, Fisher-Yates) |
| `encodeAnswers` / `decodeAnswers` | code compact pour `#r=` (version + réponses + poids), décodage tolérant et validé |

Tests de propriétés prévus :
- proximité ∈ [0, 100] ; symétrie utilisateur/candidat ; invariance si tous les poids sont multipliés par k > 0 ; réponses identiques → 100 ; extrêmes opposés partout → 0 ; ajouter une affirmation où l'un des deux est `null` ne change rien ; couverture correcte.
- projection A ∈ [-10, 10] ; antisymétrie (v → -v donne (x, y) → (-x, -y)) ; tout « +2 dans le sens de l'axe » → +10 ; **même fonction pour candidats et utilisateur** (aucun chemin de code séparé).
- projection B : sur une matrice jouet dont l'ACP est connue à la main, résultats attendus ; bornage signalé.
- `decodeAnswers(encodeAnswers(a)) == a` ; code corrompu → erreur typée, pas d'exception brute.
- shuffle : permutation valide, déterministe pour une graine, toutes les positions atteintes sur de nombreuses graines.

Couverture Vitest ≥ 90 % (seuil bloquant dans la config).

Le calcul des chargements ACP (mode B) est fait côté pipeline (numpy) en M1 aussi, sur la démo : `pipeline build` produit `pca_model.json`, testé par pytest avec la même matrice jouet que le test TS (fixture partagée dans `schemas/fixtures/`).

### 3.2 Interface (`apps/web`)
- Chargement des données : loader typé (types générés), validation au chargement, filtrage des statuts (§ 1).
- **Questionnaire** : groupé par thème (ordre de la config), progression par thème, Likert 5 niveaux + « Sans avis », pondération par thème, navigation clavier complète.
- **Persistance** : état en mémoire ; case « Sauvegarder sur cet appareil » désactivée par défaut (localStorage) ; export/import du code `#r=` (fragment jamais envoyé au serveur, vérifié par test Playwright sur les requêtes réseau).
- **Résultats** : liste des proximités dans l'ordre aléatoire de session, couverture et avertissement < 50 %, bascule mode A / mode B (avec interprétation des axes et variance expliquée en mode B).
- **Échiquier D3** : quadrants nommés, points candidats couleur + forme, marqueur utilisateur, cercles de proximité, filtre par thème, clic → panneau latéral (accords, désaccords, silences, citations).
- **Tableau accessible** équivalent (trié à la demande, clavier) et description textuelle de la position.
- **Mode aveugle** : alias, palette neutre, documents masqués, bouton « Révéler ». Implémenté par une seule fonction de présentation `displayCandidate(c, blind)` utilisée partout (pas de `c.name` en direct dans les composants, vérifié par une règle ESLint).
- **« Et si… »** : modifier réponse ou poids sur l'écran de résultats, recalcul immédiat, trace animée ancien → nouveau point (respect de `prefers-reduced-motion`), delta de proximité par candidat.

### 3.3 Tests front
- Vitest + Testing Library : loader, `displayCandidate`, composants questionnaire.
- Playwright : parcours complet (desktop + mobile 360 px), mode aveugle (aucun nom réel dans le DOM), « Et si », export/import `#r=`, **aucune requête réseau sortante après le chargement initial** (interception des requêtes), axe-core sans violation sur chaque écran.

### 3.4 Critères d'acceptation M1
- [ ] Tests moteur verts, couverture ≥ 90 % (sortie fournie).
- [ ] Playwright + axe verts en CI.
- [ ] Parcours fonctionnel en local (`pnpm dev`), captures d'écran desktop et mobile jointes.
- [ ] Revue `relecteur` sans problème bloquant.

> 📝 Annotation : ok

## 4. M2 : Ingestion, rag-service, chat RAG (corpus 2022)

Grandes lignes, détaillées à l'ouverture du jalon :
1. **Corpus 2022** : constituer `data/elections/fr-presidentielle-2022/election_config.json` (12 candidats, programmes + professions de foi officielles archivées, URL + sha256). Tâche manuelle d'abord : je propose la liste des sources, tu valides.
2. **Pipeline** `fetch`, `extract` (PyMuPDF / trafilatura, n° de page), `chunk` (300-600 tokens, métadonnées obligatoires, test qui rejette un chunk incomplet), `embed` + `index` (Postgres, HNSW + GIN).
3. **Modèle d'embedding** : intégrer `bge-m3` et `multilingual-e5-large` derrière une interface commune ; le choix définitif se fait en M4.
4. **rag-service** : `/embed`, `/retrieve` (top-k par candidat, hybride pgvector + FTS `french`, fusion RRF), tests sur base de test Docker.
5. **`/api/ask`** (Next.js) : rate limit en mémoire, plafond `DAILY_BUDGET_USD`, cache LRU mémoire (§ 6.2 bis), prompt `prompts/rag_system.md` versionné, blocs `document` + citations natives, jetons `{{cN}}`, post-validation des citations, streaming SSE, **aucun log du contenu des questions** (test qui inspecte les logs émis).
6. **UI chat** : historique client 3 tours, citations cliquables, marquage « non vérifiée », compatible mode aveugle.

Coût estimé du jalon : développement et tests manuels du chat sur Haiku, **< 2 $** (quelques centaines de questions à ≈ 0,0024 $). Le prompt, les modèles et les paramètres Claude seront vérifiés contre la doc API à jour au moment de l'implémentation.

> 📝 Annotation : ok

## 5. M3 : Positions, mesures, revue ; comparateur et radar

1. Rédaction des affirmations 2022 : Claude propose 30 affirmations conformes aux règles de couverture, **tu valides**.
2. `propose-positions` et `propose-measures` (Sonnet 5.5, Batch API, sortie structurée validée par les schémas) ; prompts versionnés dans `prompts/`.
3. `review` : page locale `/admin/review` (désactivée en prod par variable d'environnement **et** absente du build prod) ou CLI ; décisions tracées.
4. `build` : JSON validés + `pca_model.json` pour 2022.
5. Comparateur face-à-face et grille radar (pictogramme + libellé texte).

Coût estimé : **≈ 10-20 $** (positions + mesures pour 2022, éventuelles relances).

> 📝 Annotation : ok

## 6. M4 : Backtest 2022

Jeu d'environ 60 questions annotées (dont pièges sur silences), codage manuel de référence d'un échantillon de positions (par toi), comparaison CHES (lrecon / galtan), neutralité par permutation, profils synthétiques. Comparaisons : 2 modèles d'embedding, Haiku vs Sonnet. Rapport `eval/reports/<date>.md` reproductible.

Coût estimé : **≈ 10-30 $ par run complet** ; je prévois 2 à 3 runs.

> 📝 Annotation : ok

## 7. M5 : Accessibilité, méthodologie, déploiement

Audit RGAA manuel en plus d'axe, `docs/methodologie.md` + page publique, `docker-compose.prod.yml` + Caddy (TLS), durcissement (en-têtes CSP stricts, pas de log d'IP), déploiement VPS documenté. Prérequis de ton côté : VPS et domaine `moi-electeur.fr` réservé.

Coût : VPS ≈ 8-15 € / mois, domaine ≈ 10 € / an.

> 📝 Annotation : ok

## 8. M6 : Présidentielle 2027

Création de `fr-presidentielle-2027` dès la publication des programmes, même chaîne que 2022 (affirmations, propositions, revue, build). Calendrier dépendant des candidats.

> 📝 Annotation : ok

## 9. Risques identifiés

| Risque | Mitigation |
|---|---|
| Sources 2022 introuvables ou retirées | Archives (Wayback Machine, CNCCEP pour les professions de foi), sha256 conservé |
| Mode B (ACP) peu interprétable avec 12 candidats et 30 affirmations | Affichage de la variance expliquée et des affirmations contributives ; mode A par défaut |
| Image Docker du service RAG lourde (torch + modèle) | Torch CPU uniquement, modèle téléchargé dans un volume (`models/`, ignoré par git) |
| Biais des affirmations rédigées par LLM | Validation humaine, sens alternés, mesure en backtest (profils synthétiques) |
| Dérive entre schémas et types | Génération + vérification de dérive en CI (D6) |

> 📝 Annotation : ok
