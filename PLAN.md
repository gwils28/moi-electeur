# PLAN de Moi Électeur

> Statut : **v0.3, validé** (2026-11-19 : M2 détaillé, décisions D11 à D21 acceptées ; v0.2 validée le 2026-11-17 : décisions D1 à D10, § 1 bis notebooks R&D ; M0 et M1 livrés). Dérivé de [SPEC.md](SPEC.md) v0.2.
> Mode d'emploi : annoter directement sous les blocs `> 📝 Annotation :` (ou n'importe où). Rien n'est implémenté avant ton retour.
> Niveau de détail : M0, M1 et M2 détaillés, M3 à M6 en grandes lignes, détaillés au moment venu.

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
- [x] `pnpm check` vert ; `uv run pytest` vert (sorties collées dans la PR).
- [x] `docker compose up -d` : `db` healthy, `curl localhost:8000/health` → 200, `localhost:3000` répond.
- [x] `uv run pipeline validate data/elections/demo-fictive` vert ; un fichier volontairement cassé est rejeté (test).
- [x] Le test « zéro I/O » échoue si on ajoute `fetch` dans `packages/engine` (vérifié puis retiré).
- [x] CI verte sur la PR (#3, 2026-11-17).

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
- [x] Tests moteur verts, couverture ≥ 90 % (sortie fournie).
- [x] Playwright + axe verts en CI (#3, 2026-11-17).
- [x] Parcours fonctionnel en local (`pnpm dev`), captures d'écran desktop et mobile jointes.
- [x] Revue `relecteur` sans problème bloquant.

> 📝 Annotation : ok

## 4. M2 : Ingestion, rag-service, chat RAG (corpus 2022)

Objectif : poser une question en français dans `/explorer` et recevoir, en streaming, une réponse neutre couvrant chaque candidat 2022, chaque affirmation étant adossée à une citation vérifiée d'un document officiel (titre, page, lien). **Coût LLM < 2 $** (Haiku, tests manuels uniquement ; aucun appel réel en CI).

### 4.0 Décisions à trancher (M2)

| # | Sujet | Proposition | Alternative |
|---|---|---|---|
| D11 | Liste des sources 2022 | **Proposée dans `docs/sources-2022.md`** (une ligne par document : URL d'origine, URL d'archive, statut), tu valides ligne par ligne, puis `pipeline add-source` remplit `election_config.json` | Saisie directe dans `election_config.json` |
| D12 | Ajout d'une source | **`pipeline add-source <election> <candidat> <url> --title … --type …`** télécharge, calcule le sha256 et écrit l'entrée `corpus` complète : le schéma reste strict (sha256 obligatoire), aucune saisie manuelle de hash | Rendre `sha256` / `retrieved_at` facultatifs jusqu'au premier `fetch` |
| D13 | Élection « corpus seul » | **2022 existe en M2 sans `statements` / `positions` / `measures`** : `validate` et `build` les tolèrent absents (contrôles de couverture ignorés, boussole non publiée pour cette élection), ils deviennent obligatoires dès qu'un des trois existe | Rédiger un brouillon d'affirmations 2022 dès M2 |
| D14 | Stockage des embeddings | **Table `chunks` (texte + métadonnées + `tsv`) et table `chunk_embeddings(chunk_id, model, embedding vector(1024))`**, un index HNSW partiel par modèle : `bge-m3` et `multilingual-e5-large` (tous deux en 1024 dimensions) coexistent pour la comparaison M4. Écart à SPEC § 4.5 (une colonne `embedding` dans `chunks`), SPEC corrigée après validation | Une base ou une colonne par modèle |
| D15 | Code d'embedding partagé | **Module `moi_electeur_rag.embedding`** (interface `Embedder` : `embed_documents`, `embed_query`, préfixes `query:` / `passage:` pour e5) importé par le pipeline (dépendance de workspace uv) : une seule implémentation pour l'indexation et la requête. Les tests utilisent un `FakeEmbedder` déterministe ; aucun modèle réel n'est téléchargé en CI | Le pipeline appelle `/embed` du service |
| D16 | Thème des chunks | **Similarité d'embedding avec une courte description par thème** (champ facultatif `description` ajouté au thème dans `election_config.schema.json`), `theme = null` si la marge entre les deux meilleurs thèmes est faible. **Pas de LLM en M2** ; l'arbitrage LLM des cas ambigus (SPEC § 8.3) est reporté et mesuré en M4 | Classifieur LLM dès M2 (coût faible mais non nul) |
| D17 | Mesure des 300-600 tokens | **Tokenizer XLM-RoBERTa**, commun aux deux modèles candidats (même découpage quel que soit le modèle retenu) | Approximation en mots |
| D18 | Schéma SQL | **SQL brut versionné** (`services/rag/sql/NNN_*.sql`), appliqué par `uv run pipeline db-migrate` (table `schema_migrations`), driver `psycopg` 3 ; pas d'ORM ni d'Alembic | SQLAlchemy + Alembic |
| D19 | Tests avec base | **Marqueur pytest `db`** : base éphémère créée par test de session sur le Postgres du compose en local, service container `pgvector/pgvector:pg16` en CI ; ignorés avec un message clair si aucune base n'est joignable en local, **jamais ignorés en CI** | testcontainers-python |
| D20 | PDF sans couche texte | **Détecté par `extract`, signalé et exclu** (pas d'OCR en M2) ; si un document indispensable est concerné, OCR (`tesseract`) ajouté en écart consigné | OCR systématique |
| D21 | Sous-lots et branches | **Quatre PR** : `feat/m2a-ingestion` (4.1-4.2), `feat/m2b-rag-service` (4.3-4.4), `feat/m2c-api-ask` (4.5), `feat/m2d-chat-ui` (4.6-4.7) | Une seule PR M2 |

> 📝 Annotation : OK

### 4.1 Corpus 2022 (`data/elections/fr-presidentielle-2022/`)
- `docs/sources-2022.md` : pour chaque candidat, la **profession de foi du 1er tour** (source État en priorité) et le **programme principal** (archive Wayback Machine, URL brute `id_/`), plus les livrets complémentaires à trancher. Uniquement des documents du candidat, de son parti ou de l'État (SPEC § 1, non-objectifs).
- `election_config.json` : 12 candidats (`id`, `name`, `party`, `color` neutre par défaut, `program_url`, `blind_alias`), mêmes axes, quadrants et thèmes que la démo (+ descriptions D16), `corpus` rempli par `add-source` (D12).
- Les fichiers téléchargés vont dans `data/elections/<id>/sources/` (déjà ignoré par git, pas de redistribution) ; seuls URL et sha256 sont versionnés.

### 4.2 Pipeline d'ingestion (`pipeline`), test d'abord
| Commande | Rôle | Tests clés |
|---|---|---|
| `add-source` | télécharge, hash, ajoute l'entrée `corpus` (refuse un doublon d'URL ou de sha256) | entrée conforme au schéma ; doublon refusé ; réseau simulé |
| `fetch <election>` | télécharge ce qui manque, **vérifie le sha256** (échec explicite si le document a changé), idempotent | sha256 faux → erreur ; fichier présent et correct → aucun téléchargement |
| `extract <election>` | PDF : PyMuPDF, texte par page, titres repérés par la taille de police ; HTML : trafilatura ; sortie JSONL `pages` (`document`, `page_number`, `text`, `headings`) dans `sources/` | fixtures PDF/HTML minimales générées dans les tests ; PDF sans texte → signalé (D20) |
| `chunk <election>` | découpe par sections puis fenêtres de 300-600 tokens (D17), chevauchement ≈ 50 tokens, jamais à cheval sur deux documents ; un chunk peut couvrir deux pages (`page_number` = première page, `page_end` conservé) | **chunk sans métadonnée obligatoire rejeté** ; bornes de taille ; texte reconstruit sans perte ; déterminisme |
| `index <election> --model bge-m3` | embeddings (D15), thème (D16), écriture `chunks` + `chunk_embeddings` dans une transaction ; réindexation = remplacement complet de l'élection pour ce modèle ; **version du corpus** = hash des sha256 et des paramètres de découpage, écrite en base | idempotence ; version de corpus stable ; `FakeEmbedder` |
| `db-migrate` | applique les scripts SQL (D18) | migrations rejouables, schéma attendu présent |

Table `chunks` : `id, election_id, candidate_id, document_title, source_url, page_number, page_end, section_title, theme (nullable), text, tsv (tsvector 'french', colonne générée), token_count, corpus_version`. Index GIN sur `tsv`, B-tree sur `(election_id, candidate_id)`.

### 4.3 Modèles d'embedding
- `bge-m3` et `multilingual-e5-large` via `sentence-transformers`, **torch CPU uniquement** (index `download.pytorch.org/whl/cpu` dans uv), poids téléchargés dans `models/` (ignoré par git, volume Docker).
- Normalisation L2, distance cosinus. Modèle par défaut du service : variable `EMBEDDING_MODEL` (défaut `bge-m3`, choix définitif en M4).
- Un test « vrai modèle » marqué `model`, lancé à la main seulement (≈ 2 Go par modèle).

### 4.4 rag-service (`services/rag`)
- `POST /retrieve` : `{ election_id, question, candidate_ids?, theme?, k = 4 }` → par candidat : top 20 sémantique (HNSW) et top 20 FTS (`websearch_to_tsquery('french', …)`), **fusion RRF (k = 60)**, garde les `k` meilleurs ; renvoie chunks + métadonnées + `corpus_version`. La récupération par candidat garantit qu'aucun candidat n'est absent faute de score.
- `POST /embed` : utilitaire de débogage, désactivé hors dev.
- Accès réseau : écoute sur le réseau Docker interne uniquement en prod (M5) ; en dev, `127.0.0.1:8000`.
- **Aucun log du corps des requêtes** : journal d'accès uvicorn limité (méthode, chemin, code, latence) ; test qui capture les logs d'une requête `/retrieve` et vérifie que la question n'y figure pas.
- Tests : RRF sur des classements jouets calculés à la main ; couverture par candidat (un candidat sans résultat FTS reste présent) ; filtres candidat et thème ; tests `db` avec `FakeEmbedder`.

### 4.5 `/api/ask` (Next.js, runtime Node)
- Seule partie dynamique de l'application ; la boussole reste statique. Clé `ANTHROPIC_API_KEY` lue côté serveur uniquement, modèle `CHAT_MODEL` (défaut `claude-haiku-5-5`). SDK `@anthropic-ai/sdk`, client injecté pour être simulé dans les tests.
- Chaîne : validation de l'entrée (longueur ≤ 500 caractères, 3 tours d'historique max) → **rate limit** (10 questions / 10 min par IP, compteur en mémoire, IP jamais écrite) → **plafond `DAILY_BUDGET_USD`** (coût calculé depuis l'`usage` renvoyé par l'API et une table de tarifs versionnée ; au-delà, message clair et code 503) → **cache LRU** (§ 6.2 bis, première question seulement) → `/retrieve` → appel Claude en streaming → relais SSE.
- **Prompt** `prompts/rag_system.md` (en-tête `version:`), consignes SPEC § 6.2 : extraits seuls, phrase exacte pour les silences, ton encyclopédique, ordre des candidats imposé (**tiré au sort par requête côté serveur**), longueur comparable, noms remplacés par `{{cN}}`.
- **Extraits en blocs `document` avec citations natives** (un bloc par chunk, titre `{{cN}} · <document> · p. X`) ; post-validation : chaque `cited_text` doit être une sous-chaîne (espaces normalisés) d'un chunk renvoyé, sinon marqué « non vérifiée ». En mode aveugle, les citations restent masquées côté client (décision M1).
- Garde-fou de neutralité en sortie : la liste de mots interdits (§ 1) est vérifiée sur la réponse complète ; une occurrence est signalée dans la réponse (pas de réécriture silencieuse) et comptée dans les métriques.
- **Logs** limités à : horodatage, modèle, tokens in/out, coût, latence, code retour, cache hit. Test qui capture tout ce que la route écrit (console et logger) et vérifie l'absence de la question et de l'historique.
- Format du flux SSE documenté (`delta`, `citation`, `done`, `error`), types TS dans `apps/web/src/lib/rag/`.
- Les détails d'API (blocs `document`, citations, streaming, `max_tokens`, tarifs) sont vérifiés contre la doc Claude à jour au moment d'écrire la route.

### 4.6 UI chat (`/explorer`)
- Sélecteur d'élection limité aux élections indexées (2022 en M2 ; la démo fictive n'a pas de corpus), filtres candidats et thème.
- Réponse streamée, jetons `{{cN}}` remplacés par `displayCandidate` (nom ou alias), citations cliquables (document, page, lien vers l'archive), badge « non vérifiée », historique client de 3 tours, rien en `localStorage`.
- Mentions visibles : réponses générées automatiquement à partir des seuls programmes officiels, peuvent contenir des erreurs, lien vers la source.
- Accessibilité : zone `aria-live="polite"` pendant le streaming, envoi au clavier, axe-core.

### 4.7 Notebooks M2 et jeu de fumée
- `m2-01-extraction-chunks.py` (qualité d'extraction par document, distribution des tailles, cas limites), `m2-02-embeddings.py` (bge-m3 vs e5 sur un jeu de fumée), `m2-03-retrieval-rrf.py` (sémantique seul, FTS seul, RRF), `m2-04-prompt-neutralite.py` (réponses enregistrées dans `notebooks/fixtures/`, aucun appel réel en CI).
- `eval/smoke/questions-2022.jsonl` : ≈ 15 questions avec candidats et pages attendus, dont 3 pièges sur des silences et 2 demandes de recommandation (« pour qui voter ? ») ; sert de test de non-régression du retrieval (rappel@k mesuré, sans LLM). Le jeu complet (≈ 60) arrive en M4.

### 4.8 Docker et CI
- `rag` : image avec torch CPU, volume `models/`, variable `EMBEDDING_MODEL` ; healthcheck qui vérifie aussi la connexion à la base.
- `web` : passe de « statique pur » à `next start` avec la route API (déjà le cas en dev) ; `ANTHROPIC_API_KEY` via `.env` (jamais commitée, `.env.example` sans valeur).
- CI : service container pgvector pour les tests `db` ; dérive des types (nouveau champ `description` des thèmes) ; notebooks M2 exécutés sur fixtures.

### 4.9 Critères d'acceptation M2
- [x] `docs/sources-2022.md` validé, `pipeline fetch` vérifie les 12 candidats (sha256 OK), `pipeline validate` vert sur 2022 (M2a, 2026-11-19 : 24 documents).
- [ ] `extract` + `chunk` + `index` sur 2022 avec les deux modèles ; aucun chunk sans métadonnée ; rapport de couverture (pages et chunks par candidat) dans le notebook m2-01.
- [ ] `/retrieve` renvoie au moins un chunk par candidat sur chaque question du jeu de fumée ; rappel@4 mesuré pour les deux modèles et RRF vs sémantique seul (chiffres dans les notes).
- [ ] `/api/ask` : tests verts (rate limit, budget, cache, post-validation, absence de logs de question) avec client Anthropic simulé.
- [ ] Parcours manuel dans `/explorer` sur Haiku, captures jointes, coût réel relevé (< 2 $).
- [ ] Playwright + axe sur `/explorer` (réponse simulée), CI verte, revue `relecteur` sans problème bloquant.

Coût estimé du jalon : **< 2 $** (quelques centaines de questions à ≈ 0,0024 $). Coût de calcul : indexation 2022 en CPU estimée à quelques minutes par modèle (corpus de quelques centaines de pages).

> 📝 Annotation : OK

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
