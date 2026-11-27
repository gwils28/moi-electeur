import { NextResponse, type NextRequest } from "next/server";

/**
 * CSP stricte à nonce (PLAN D49) : un nonce par requête, que Next applique à ses propres
 * scripts ; aucun `unsafe-inline` ni `unsafe-eval` pour les scripts en production. Les styles
 * gardent `unsafe-inline` (attributs `style` de React, risque limité). Aucune ressource tierce
 * (SPEC § 11) : tout vient de l'origine du site.
 */
export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const dev = process.env.NODE_ENV === "development";
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' blob: data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    // Production derrière TLS (docker-compose.prod.yml) ; pas en local, servi en HTTP.
    ...(process.env.CSP_UPGRADE_INSECURE === "1" ? ["upgrade-insecure-requests"] : []),
  ].join("; ");

  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce);
  headers.set("Content-Security-Policy", csp);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: [
    {
      source: "/((?!api|_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
