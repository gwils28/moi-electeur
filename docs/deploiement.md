# Déploiement (VPS)

Procédure de mise en ligne de Moi Électeur sur un serveur unique (PLAN D48 à D50) : quatre
conteneurs (Caddy, front Next.js, service de recherche, PostgreSQL avec pgvector), seul Caddy
étant exposé, en HTTPS avec un certificat Let's Encrypt automatique.

## 1. Prérequis

- **Serveur** : 4 vCPU, 8 Go de mémoire, 40 Go de disque (Debian 12 ou Ubuntu 24.04), avec
  Docker Engine et le plugin Compose. Le service de recherche charge le modèle d'embedding
  (environ 2,2 Go en mémoire) ; l'indexation du corpus se fait une fois.
- **Domaine** : enregistrements DNS `A` (et `AAAA` si IPv6) de `moi-electeur.fr` et
  `www.moi-electeur.fr` vers l'adresse du serveur, propagés avant le premier démarrage (Caddy
  obtient le certificat au démarrage).
- **Pare-feu** : ports 22 (SSH), 80 et 443 (TCP) et 443 (UDP, HTTP/3) ouverts ; tout le reste
  fermé. La base et le service de recherche ne publient aucun port.
- **Clé API Claude** (facultative) : sans clé, le chat répond « indisponible » et le reste du
  site fonctionne. Fixer une limite de dépense mensuelle dans la console Anthropic.

## 2. Installation

```sh
git clone https://github.com/gwils28/moi-electeur.git && cd moi-electeur
cp .env.example .env    # puis renseigner les variables ci-dessous (jamais commité)
```

Variables de `.env` pour la production :

| Variable | Rôle |
|---|---|
| `DOMAIN` | domaine servi, par exemple `moi-electeur.fr` (obligatoire) |
| `ACME_EMAIL` | adresse pour les avis de Let's Encrypt (obligatoire) |
| `POSTGRES_PASSWORD` | mot de passe de la base, long et aléatoire (obligatoire) |
| `ANTHROPIC_API_KEY` | clé du chat (facultative) |
| `CHAT_MODEL` | modèle du mode rapide (défaut `claude-haiku-5-5`) |
| `CHAT_MODEL_BOOST` | modèle du mode détaillé (vide : mode non proposé) |
| `DAILY_BUDGET_USD`, `DAILY_BUDGET_BOOST_USD` | plafonds quotidiens du chat (coupure au-delà) |
| `EMBEDDING_MODEL` | défaut `multilingual-e5-large` (PLAN D37) |

## 3. Données et index de recherche

Le front et la boussole n'ont besoin d'aucune étape : les JSON validés sont produits pendant la
construction de l'image. Le chat a besoin du corpus indexé :

```sh
# Sur le serveur, avec uv (https://docs.astral.sh/uv/) : documents, extraits, poids du modèle.
uv sync --all-packages
uv run pipeline fetch data/elections/fr-presidentielle-2022   # télécharge et vérifie le sha256
uv run pipeline extract data/elections/fr-presidentielle-2022
uv run pipeline chunk data/elections/fr-presidentielle-2022
```

Les poids du modèle d'embedding sont téléchargés dans `models/` à la première indexation, que
l'on lance une fois la base démarrée (étape 4) :

```sh
docker compose -f docker-compose.prod.yml --env-file .env up -d db
DATABASE_URL=postgresql://moi_electeur:<mot de passe>@localhost:5432/moi_electeur \
  uv run pipeline db-migrate
```

La base de production n'expose aucun port : pour l'indexation, publier temporairement le port
5432 sur `127.0.0.1` (surcharge locale de `docker-compose.prod.yml`), ou lancer l'indexation dans
un conteneur relié au réseau interne. Puis :

```sh
uv run pipeline index data/elections/fr-presidentielle-2022 --model multilingual-e5-large
```

## 4. Démarrage

```sh
docker compose -f docker-compose.prod.yml --env-file .env up -d --build --wait
scripts/deploy-check.sh https://moi-electeur.fr
```

`deploy-check.sh` vérifie le HTTPS et la redirection HTTP, les en-têtes de sécurité (HSTS, CSP à
nonce sans `unsafe-inline` pour les scripts, `frame-ancestors 'none'`, `nosniff`,
`Referrer-Policy`, `Permissions-Policy`, absence d'en-tête `Server` et de cookie), les pages et
la route du chat.

## 5. Sécurité et confidentialité

- **En-têtes** : la CSP est posée par l'application (`apps/web/src/proxy.ts`, nonce par requête,
  pages rendues à la demande) ; les autres en-têtes par Caddy (`Caddyfile`).
- **Journaux** : Caddy n'écrit ni adresse IP, ni en-têtes, ni chaîne de requête ; l'application
  n'écrit jamais la question posée au chat (une ligne par requête : horodatage, modèle, tokens,
  coût, latence, code retour). Le limiteur de débit garde les adresses en mémoire seulement.
- **Secrets** : uniquement dans `.env` sur le serveur (droits `600`), jamais dans le dépôt.
- **Réseau** : base et service de recherche sur un réseau Docker interne, sans accès extérieur.

## 6. Mise à jour

```sh
git pull
docker compose -f docker-compose.prod.yml --env-file .env up -d --build --wait
scripts/deploy-check.sh https://moi-electeur.fr
```

Après une modification du corpus (nouveau découpage), relancer `pipeline index` ; après une revue
de positions, la reconstruction de l'image suffit (`pipeline build` y est exécuté).

## 7. Sauvegarde

Seule la base contient un état propre au serveur (index du corpus, reconstructible à partir du
dépôt et des documents sources). Sauvegarde ponctuelle :

```sh
docker compose -f docker-compose.prod.yml --env-file .env exec db \
  pg_dump -U moi_electeur moi_electeur | gzip > sauvegarde-$(date +%F).sql.gz
```

Les certificats sont dans le volume `caddy-data` ; leur perte entraîne seulement une nouvelle
émission automatique.

## 8. Essai local de la stack de production

Sans domaine, avec `DOMAIN=localhost` (certificat émis par l'autorité interne de Caddy) et, si
les ports 80 et 443 sont pris, une surcharge qui publie Caddy sur 8080 et 8443 :

```sh
DOMAIN=localhost ACME_EMAIL=essai@example.org POSTGRES_PASSWORD=essai \
  docker compose -f docker-compose.prod.yml -f surcharge-ports.yml up -d --build --wait
HTTP_URL=http://localhost:8080 scripts/deploy-check.sh https://localhost:8443 --insecure
```
