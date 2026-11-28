#!/usr/bin/env bash
# Vérifications après mise en ligne (PLAN D50) : TLS, redirection HTTP, en-têtes de sécurité,
# pages, santé du chat. Usage : scripts/deploy-check.sh https://moi-electeur.fr [--insecure]
# (--insecure : certificat non public, par exemple l'essai local avec DOMAIN=localhost).
# HTTP_URL=http://hôte:port : adresse HTTP à tester pour la redirection (défaut : même hôte, port 80).
set -u
BASE="${1:?URL du site attendue, par exemple https://moi-electeur.fr}"
CURL=(curl -sS --max-time 20)
[ "${2:-}" = "--insecure" ] && CURL+=(-k)
fails=0

check() {
  local label="$1" ok="$2"
  if [ "$ok" = "1" ]; then echo "OK    $label"; else echo "ÉCHEC $label"; fails=$((fails + 1)); fi
}

headers="$("${CURL[@]}" -D - -o /dev/null "$BASE/")" || headers=""
up="$(printf '%s' "$headers" | head -1 | grep -q ' 200' && echo 1 || echo 0)"
# Sans réponse, aucun contrôle d'en-tête ne peut réussir (pas de faux succès).
has() { [ "$up" = "1" ] && printf '%s' "$headers" | grep -qi "$1" && echo 1 || echo 0; }
lacks() { [ "$up" = "1" ] && ! printf '%s' "$headers" | grep -qiE "$1" && echo 1 || echo 0; }

check "page d'accueil en 200" "$up"
check "HSTS" "$(has '^strict-transport-security: max-age=')"
check "CSP à nonce" "$(has "^content-security-policy:.*script-src 'self' 'nonce-")"
csp_scripts="$(printf '%s' "$headers" | grep -i '^content-security-policy:' | grep -o "script-src[^;]*")"
check "CSP sans unsafe-inline pour les scripts" \
  "$([ "$up" = "1" ] && [ -n "$csp_scripts" ] && ! printf '%s' "$csp_scripts" | grep -q unsafe && echo 1 || echo 0)"
check "frame-ancestors 'none'" "$(has "frame-ancestors 'none'")"
check "X-Content-Type-Options: nosniff" "$(has '^x-content-type-options: nosniff')"
check "Referrer-Policy: no-referrer" "$(has '^referrer-policy: no-referrer')"
check "Permissions-Policy" "$(has '^permissions-policy:')"
check "aucun en-tête Server ni X-Powered-By" "$(lacks '^(server|x-powered-by):')"
check "aucun cookie déposé" "$(lacks '^set-cookie:')"

for path in /comparateur /positions /interrogatoire /methodologie /accessibilite; do
  code="$("${CURL[@]}" -o /dev/null -w '%{http_code}' "$BASE$path")"
  check "$path en 200" "$([ "$code" = "200" ] && echo 1 || echo 0)"
done

# Chat : un GET sur /api/ask n'est pas une question (405 attendu, jamais 5xx).
code="$("${CURL[@]}" -o /dev/null -w '%{http_code}' "$BASE/api/ask")"
check "/api/ask répond (405 sur GET)" "$([ "$code" = "405" ] && echo 1 || echo 0)"

host="${BASE#https://}"
if [ "$host" != "$BASE" ]; then
  http_url="${HTTP_URL:-http://${host%%:*}}"
  code="$("${CURL[@]}" -o /dev/null -w '%{http_code}' "$http_url/")"
  check "HTTP redirigé vers HTTPS" "$([ "$code" = "308" ] || [ "$code" = "301" ] && echo 1 || echo 0)"
fi

echo
if [ "$fails" -eq 0 ]; then echo "Tout est conforme."; else echo "$fails vérification(s) en échec."; fi
exit "$fails"
