# SPEC de Moi Électeur (Boussole & Explorateur de Programmes)

> Statut : **v0.2, points ouverts tranchés** (2026-11-17). Issu de l'interview du 2026-11-17.
> Nom public : **Moi Électeur**, domaine visé `moi-electeur.fr` (libre au 2026-11-17, à réserver).

## 1. Objectif

Application web civic tech d'aide à la décision électorale, fondée **exclusivement sur les programmes officiels** des candidats :
1. une **boussole** (questionnaire → proximité → échiquier 2D), calculée 100 % dans le navigateur ;
2. un **explorateur conversationnel** (RAG sourcé, neutre, citations obligatoires) ;
3. des outils complémentaires : mode aveugle, simulateur « Et si », comparateur face-à-face, radar chiffrages.

Cible : **Présidentielle française 2027**. Validation : **backtest sur élections passées** (Présidentielle 2022, puis 2017).

### Non-objectifs
- Pas de compte utilisateur, pas de persistance des réponses, pas de profilage.
- Pas de recommandation de vote, aucun classement « meilleur / pire ».
- Pas de sources non officielles (presse, interviews) dans le corpus RAG.

## 2. Décisions d'architecture (issues de l'interview)

| Sujet | Décision |
|---|---|
| Élection cible | Présidentielle 2027 ; 2022 et 2017 pour le backtest |
| LLM (chat RAG) | Claude API. Modèle configurable par env, **défaut `claude-haiku-5-5`** ; Sonnet 5.5 évalué en backtest |
| LLM (pipeline hors ligne) | `claude-sonnet-5-5` (extraction positions / chiffrages), via Batch API (-50 %) |
| Embeddings | Modèle local open-source multilingue (candidat : `BAAI/bge-m3` ou `intfloat/multilingual-e5-large`, choix par backtest) |
| Base vectorielle | PostgreSQL 16 + **pgvector** ; mots-clés via full-text search Postgres (config `french`) ; fusion **RRF** |
| Hébergement | VPS + Docker Compose ; même stack en local et en prod |
| Front | Next.js (App Router, TypeScript strict) + Tailwind CSS + D3.js (échiquier) |
| Pipeline & backtest | Python 3.12+, géré avec `uv` |
| Positions candidats | **LLM propose + humain valide** (fichier de revue versionné) |
| Affirmations | Claude propose, l'utilisateur valide |
| Projection 2D | **Deux modes commutables** : (A) affirmations taguées axe/sens ; (B) analyse factorielle (ACP) |
| Dépôt | GitHub public. Code : **AGPL-3.0** ; données dérivées (positions, mesures, affirmations, jeux d'éval) : **CC BY-SA 4.0**. Les programmes originaux ne sont pas redistribués (URL + sha256 seulement) |
| Revue humaine | Un seul relecteur (le mainteneur) pour l'instant ; chaque décision reste tracée (`reviewer`, `date`, `note`) pour ouvrir à des contributeurs plus tard |
| Monorepo | Workspaces **pnpm** ; moteur de calcul dans `packages/engine` |
| Audience | Restreinte au départ ; coûts plafonnés et estimés (§ 10) |
| UX / conformité | Écran PC & mobile, RGAA / WCAG 2.1 AA, page méthodologie publique, zéro cookie / tracking |

## 3. Architecture

```
Navigateur ──────────────────────────────────────────────────────────┐
  Questionnaire, pondération, proximité, projection, mode aveugle,   │  100 % client
  « Et si », comparateur, radar  (données statiques JSON)            │  aucune réponse envoyée
                                                                      │
  Chat RAG ──POST question──▶ Next.js API route /api/ask ────────────┘
                                 │ 1. rate limit + plafond budget
                                 │ 2. POST /retrieve ──▶ rag-service (FastAPI, Python)
                                 │                         embed requête (modèle local)
                                 │                         hybride pgvector + FTS, RRF
                                 │                         ◀── chunks + métadonnées
                                 │ 3. Claude (streaming SSE) ◀── prompt système neutralité
                                 ▼
                           réponse streamée + citations

Hors ligne (pipeline Python) : sources → extraction → chunks → embeddings → Postgres
                               → proposition positions/chiffrages (Claude) → revue humaine
                               → JSON statiques validés (servis au front)
```

Services Docker Compose : `web` (Next.js), `rag` (FastAPI + modèle d'embedding), `db` (Postgres + pgvector), `caddy` (reverse proxy TLS, prod uniquement).

## 4. Modèle de données

### 4.1 `data/elections/<election_id>/election_config.json`
Validé par JSON Schema (`schemas/election_config.schema.json`), types TS et Pydantic générés depuis ce schéma (source unique).

```jsonc
{
  "id": "fr-presidentielle-2027",
  "name": "Élection présidentielle 2027",
  "country": "FR",
  "date_first_round": "2027-04-xx",
  "axes": {
    "x": { "label": "Économie", "min_label": "Interventionnisme / Redistribution", "max_label": "Libéralisme / Baisse de la fiscalité" },
    "y": { "label": "Société & souveraineté", "min_label": "Progressisme / Intégration européenne", "max_label": "Conservatisme / Autorité / Souverainisme" }
  },
  "quadrants": { "tl": "…", "tr": "…", "bl": "…", "br": "…" },
  "themes": [ { "id": "economie", "label": "Économie" }, "social", "ecologie", "europe_international", "regalien_immigration", "institutions" ],
  "candidates": [
    { "id": "c1", "name": "…", "party": "…", "color": "#…", "photo": "photos/c1.webp",
      "program_url": "https://…", "blind_alias": "Candidat·e A" }
  ],
  "corpus": [
    { "candidate_id": "c1", "document_title": "Programme officiel", "type": "pdf",
      "source_url": "https://…", "local_path": "sources/c1/programme.pdf",
      "sha256": "…", "retrieved_at": "2027-01-15" }
  ]
}
```

### 4.2 `statements.json` : 25 à 35 affirmations
```jsonc
{ "id": "s01", "theme": "economie", "text": "…", "axis": "x", "direction": 1, "weight_in_axis": 1.0 }
```
`direction` : +1 si « d'accord » pousse vers +10 sur l'axe, -1 sinon. Sens alternés pour limiter le biais d'acquiescement. Couverture : ≥ 4 affirmations par thème, ≥ 10 par axe.

### 4.3 `positions.json` : positions validées des candidats
```jsonc
{ "candidate_id": "c1", "statement_id": "s01",
  "value": 2,                       // -2..+2, ou null = silence du programme
  "confidence": "high|medium|low",
  "evidence": [ { "quote": "…", "document_title": "…", "page": 42, "chunk_id": "…" } ],
  "proposed_by": "claude-sonnet-5-5", "review": { "status": "validated|corrected|rejected", "reviewer": "…", "date": "…", "note": "…" } }
```
Le front ne charge **que** les positions `validated` ou `corrected`. Un silence (`null`) est exclu du calcul de distance pour cette affirmation (et signalé).

### 4.4 `measures.json` : mesures phares & chiffrages (comparateur + radar)
```jsonc
{ "candidate_id": "c1", "theme": "social", "title": "…", "summary": "…",
  "costing": { "status": "chiffre|partiel|intention", "amount_eur": 12000000000, "period": "par an", "quote": "…" },
  "evidence": [ … ], "review": { … } }
```

### 4.5 Chunks (Postgres)
Table `chunks` : `id, election_id, candidate_id, theme, document_title, page_number, section_title, source_url, text, tsv (tsvector french), embedding vector(N)`. Index HNSW sur `embedding`, GIN sur `tsv`.

## 5. Fonctionnalité 1 : Boussole (100 % client)

### 5.1 Questionnaire
- Likert 5 niveaux (-2 … +2) + « Neutre / Sans avis » (`null`, exclu du calcul).
- Pondération par thème ×1 / ×2 / ×3 (défaut ×1).
- Ordre des affirmations : **groupé par thème** (ordre des thèmes fixe, défini dans la config), avec indicateur de progression par thème.
- État conservé en mémoire ; option de sauvegarde **locale** (localStorage) explicite, désactivée par défaut ; export / import d'un code de réponses (URL fragment `#r=…`, jamais envoyé au serveur).

### 5.2 Proximité : distance de Manhattan normalisée pondérée
Pour un candidat c, sur l'ensemble S des affirmations où l'utilisateur **et** le candidat ont une valeur non nulle :

```
d(c)        = Σ_{s∈S} w_theme(s) · |u_s − c_s|
d_max(c)    = Σ_{s∈S} w_theme(s) · 4
proximité   = 100 · (1 − d(c) / d_max(c))
couverture  = |S| / |affirmations répondues|      → affichée ; si < 50 %, avertissement
```

### 5.3 Projection 2D : deux modes
**Mode A (affirmations taguées, défaut)** :
```
X = 10 · Σ_{s∈S_x} w(s)·dir(s)·v_s / Σ_{s∈S_x} w(s)·2      (v ∈ [-2,2] → X ∈ [-10,10])
```
idem pour Y. Formule **identique** pour candidats et utilisateur → les (x, y) candidats sont dérivés, jamais saisis.

**Mode B (ACP)** : ACP sur la matrice candidats × affirmations (silences imputés par 0, centrée). Les 2 premières composantes donnent les axes ; l'utilisateur est projeté avec les mêmes chargements. Chargements précalculés par le pipeline et embarqués en JSON (le calcul de projection reste côté client). Les axes sont présentés avec leur interprétation (affirmations les plus contributives) et la variance expliquée. Rescale [-10, 10].

### 5.4 Échiquier 2D (D3)
- 4 quadrants nommés, points candidats (couleur + forme pour daltonisme), marqueur utilisateur distinct.
- Cercles concentriques de proximité autour de l'utilisateur.
- Filtre par thème : recalcul de (x, y) et proximité sur le sous-ensemble du thème.
- Clic candidat → panneau latéral : accords / désaccords (|écart| ≤ 1 / ≥ 3), silences, avec citations sources.
- **Alternative accessible** : tableau trié des proximités + coordonnées, navigable au clavier ; description textuelle de la position.

### 5.5 Mode aveugle
Noms, photos, partis, couleurs remplacés par des alias (`blind_alias`) et une palette neutre dans : résultats, échiquier, panneau, comparateur, citations du chat (le nom du document est masqué aussi). Bouton « Révéler » explicite. Ordre d'affichage des candidats **aléatoire par session** dans tous les modes.

### 5.6 Simulateur « Et si… »
Sur l'écran de résultats, modifier une réponse ou un poids → recalcul instantané, trace animée de l'ancien au nouveau point, delta de proximité par candidat.

## 6. Fonctionnalité 2 : Chat RAG sourcé

### 6.1 Retrieval
- Embedding de la question (même modèle que l'indexation, préfixe `query:` si e5).
- Récupération **par candidat** (top-k par candidat, k≈4) pour garantir une couverture équitable, puis fusion RRF sémantique + FTS.
- Filtres optionnels : candidats sélectionnés, thème.

### 6.2 Génération
- Prompt système de neutralité versionné (`prompts/rag_system.md`), contenant : réponse uniquement à partir des extraits ; citation courte entre guillemets + référence `[Programme <Candidat>, p. X]` ; phrase exacte « Aucune proposition recensée dans le programme officiel sur ce point » pour les silences ; ton encyclopédique ; ordre des candidats imposé (aléatoire fourni par le serveur) ; longueur comparable par candidat.
- Extraits fournis sous forme de blocs `document` avec **citations natives Claude activées** → références vérifiables mécaniquement.
- Post-validation : chaque citation est vérifiée comme sous-chaîne d'un chunk récupéré ; sinon marquée « non vérifiée ».
- Streaming SSE vers le client. Historique de conversation côté client uniquement (court, 3 tours max).
- **Noms des candidats en jetons** : le modèle écrit `{{c1}}` au lieu du nom ; le client remplace par le nom ou par l'alias en mode aveugle. Une même réponse sert donc aux deux modes (et au cache), et le mode aveugle ne dépend pas d'une consigne au LLM.

### 6.2 bis Cache des réponses
- Cache **en mémoire uniquement** (LRU, 500 entrées, TTL 24 h), jamais écrit sur disque ni en base.
- Clé = SHA-256(question normalisée + filtres + modèle + version du corpus + version du prompt). Seule la réponse est conservée, sans IP ni horodatage par utilisateur.
- Une réponse servie depuis le cache est re-streamée et ne consomme pas de budget. Ne s'applique qu'à la première question d'une conversation (les suivantes dépendent de l'historique).
- Vidé à chaque redémarrage et à chaque réindexation (la version du corpus change).

### 6.3 Confidentialité du chat
Les questions posées peuvent révéler une opinion (donnée sensible, RGPD art. 9) : **aucun log du contenu des questions**. Logs serveur limités à : horodatage, tokens consommés, latence, code retour.

## 7. Comparateur face-à-face & radar chiffrages
- Sélection 2 ou 3 candidats → tableau thème × candidat : mesures phares, chiffrage annoncé, divergences (affirmations à écart ≥ 3).
- Radar : pour chaque thème × candidat, statut `chiffré / partiel / intention / silence`, calculé depuis `measures.json` validé. Présenté en **grille de pictogrammes** (thèmes en lignes, candidats en colonnes) : chaque statut a un pictogramme **et** un libellé texte (pas d'information portée par la seule couleur) ; une cellule ouvre les mesures et citations correspondantes.

## 8. Pipeline hors ligne (Python)

1. `fetch` : télécharge les sources du `corpus`, vérifie sha256, archive.
2. `extract` : PDF (PyMuPDF, avec n° de page), HTML (trafilatura), Markdown.
3. `chunk` : découpe sémantique par sections/titres, 300-600 tokens, chevauchement léger ; métadonnées obligatoires ; thème attribué par classifieur (embedding + LLM si ambigu).
4. `embed` + `index` : écriture Postgres.
5. `propose-positions` : pour chaque (candidat, affirmation) → retrieval ciblé → Claude Sonnet (Batch API, sortie structurée) → valeur, confiance, citations.
6. `propose-measures` : extraction des mesures et chiffrages par thème.
7. `review` : interface de revue (CLI ou page locale `/admin/review` désactivée en prod) → statut validated/corrected/rejected.
8. `build` : génère les JSON statiques validés + chargements ACP → `apps/web/public/data/<election>/`.

## 9. Backtest & évaluation (`eval/`)

Sur Présidentielle 2022 (12 candidats ; corpus : programmes + professions de foi officielles archivées).

| Dimension | Méthode | Métriques |
|---|---|---|
| Qualité RAG | Jeu de questions annotées (≈ 60) avec réponses attendues par candidat, dont questions « piège » sur des silences | recall@k retrieval, exactitude citation (sous-chaîne + page), taux de silences correctement détectés, taux d'hallucination (LLM juge + échantillon humain) |
| Positionnement | Positions proposées par Claude vs codage manuel de référence ; (x, y) vs Chapel Hill Expert Survey (lrecon / galtan) des partis | accord exact / ±1, kappa pondéré, corrélation de Spearman par axe |
| Neutralité | Questions identiques, ordre des candidats permuté | écart de longueur / nb citations par candidat, sentiment, LLM juge sur la symétrie |
| Profils synthétiques | Répondants types générés depuis les positions validées + bruit | % où le candidat attendu est 1er / top-3 |

Le backtest compare aussi : modèles d'embedding, Haiku vs Sonnet pour le chat. Rapport reproductible (`eval/reports/<date>.md`).

## 10. Estimation des coûts

Tarifs Claude (au 2026-11) : Haiku 5.5 = 0,10 $ / 0,50 $ par M tokens (in/out) ; Sonnet 5.5 = 2 $ / 10 $. Hypothèse requête chat : ~16 k tokens d'entrée (prompt système + ~36 extraits), ~1,5 k tokens de sortie.

| Poste | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| 1 question chat | ≈ 0,0024 $ | ≈ 0,048 $ |
| 1 000 questions | ≈ 2,40 $ | ≈ 48 $ |
| 10 000 questions / mois | ≈ 24 $ | ≈ 480 $ |

| Poste ponctuel / fixe | Estimation |
|---|---|
| Extraction positions (12 cand. × 30 affirmations, Sonnet, Batch -50 %) | ≈ 4-8 $ par élection |
| Extraction mesures & chiffrages | ≈ 5-10 $ par élection |
| Un run complet de backtest (LLM juge inclus) | ≈ 10-30 $ |
| VPS (4 vCPU / 8 Go, ex. Hetzner CX32 ou OVH) | ≈ 8-15 € / mois |
| Embeddings | 0 $ (local) |

Garde-fous : limite de débit par IP (ex. 10 questions / 10 min, compteur en mémoire, IP non persistée), **plafond budgétaire quotidien** configurable (`DAILY_BUDGET_USD`, coupure du chat au-delà avec message), `max_tokens` borné, cache mémoire des réponses (§ 6.2 bis).

## 11. Exigences non fonctionnelles
- **Privacy-by-design** : aucune réponse au questionnaire ne quitte le navigateur ; zéro cookie, zéro analytics tierce ; pas de ressources tierces chargées (polices auto-hébergées).
- **Accessibilité** : RGAA 4.1 / WCAG 2.1 AA ; audit axe-core en CI ; navigation clavier complète.
- **Responsive** : mobile ≥ 360 px et desktop.
- **Performance** : boussole utilisable hors ligne une fois chargée ; LCP < 2,5 s.
- **Neutralité** : ordre aléatoire, palette non connotée en mode aveugle, page méthodologie listant limites et biais connus.
- **Transparence** : données validées et prompts publiés dans le dépôt.

## 12. Qualité & méthode de travail
- Tests : Vitest (moteur de calcul, couverture ≥ 90 %), Playwright (parcours principaux + axe), pytest (pipeline, rag-service).
- Le moteur de calcul est **écrit test d'abord** (tests de propriétés : symétrie, bornes, invariance d'échelle des poids).
- CI GitHub Actions : lint, typecheck, tests, validation JSON Schema des données.
- Conventional Commits ; l'humain relit et commite.

## 13. Arborescence cible
```
moi-electeur/
├── apps/web/                    Next.js (UI + API route /api/ask)
│   └── src/{app,components,lib/rag}
├── packages/engine/             moteur de calcul TS pur, zéro dépendance, zéro I/O (proximité, projections A/B)
├── services/rag/                FastAPI : /embed, /retrieve
├── pipeline/                    Python : fetch, extract, chunk, index, propose, review, build
├── eval/                        backtests, jeux annotés, rapports
├── notebooks/                   notebooks R&D marimo (PLAN § 1 bis)
├── schemas/                     JSON Schemas (source unique des types)
├── prompts/                     prompts versionnés (rag_system.md, propose_positions.md…)
├── data/elections/<id>/         config, statements, positions, measures (sources/ ignorées par git)
├── docs/methodologie.md
├── docker-compose.yml, docker-compose.prod.yml, Caddyfile
└── SPEC.md, PLAN.md, CLAUDE.md
```

## 14. Jalons proposés
1. **M0** : socle (monorepo, Docker Compose, schémas JSON, CI, données fictives de démo).
2. **M1** : Moteur de calcul (test d'abord) + questionnaire + échiquier + mode aveugle + « Et si ».
3. **M2** : Pipeline d'ingestion + rag-service + chat RAG streaming (sur corpus 2022).
4. **M3** : Proposition/revue des positions et mesures ; comparateur + radar.
5. **M4** : Backtest 2022 complet, rapport, choix modèles.
6. **M5** : Accessibilité, page méthodologie, déploiement VPS.
7. **M6** : Branchement 2027 au fil de la publication des programmes.

## 15. Décisions sur les points ouverts (2026-11-17)
| # | Sujet | Décision | Justification |
|---|---|---|---|
| 1 | Licence | AGPL-3.0 (code) + CC BY-SA 4.0 (données) | Une instance hébergée modifiée doit publier son code : c'est la garantie de transparence attendue d'un outil électoral. Les données restent réutilisables avec attribution |
| 2 | Ordre des affirmations | Groupé par thème | Choix du mainteneur |
| 3 | Radar | Grille de pictogrammes | Choix du mainteneur ; plus accessible |
| 4 | Cache du chat | Oui, en mémoire seulement (§ 6.2 bis) | Économise le coût des questions fréquentes sans rien persister |
| 5 | Moteur de calcul | `packages/engine` (workspace pnpm) | Frontière nette « zéro I/O » vérifiable, tests isolés et rapides, aucun coût de performance (compilé dans le bundle via `transpilePackages`) |
| 6 | Revue humaine | Le mainteneur seul, décisions tracées | Choix du mainteneur |
| 7 | Nom / domaine | Moi Électeur, `moi-electeur.fr` | Libre au 2026-11-17 (RDAP AFNIC : 404). Repli : `moielecteur.fr` (libre aussi) |

Aucun point ouvert restant.
