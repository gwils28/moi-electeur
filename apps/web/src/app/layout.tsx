import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { connection } from "next/server";
import type { ReactNode } from "react";
import { MainNav } from "@/components/MainNav";
import { fr } from "@/i18n/fr";
import "./globals.css";

export const metadata: Metadata = { title: fr.appName, description: fr.tagline };

export default async function RootLayout({ children }: { children: ReactNode }) {
  // Rendu à chaque requête : le nonce de la CSP (proxy.ts) n'existe pas au build.
  await connection();
  return (
    <html lang="fr">
      <body>
        <a
          href="#contenu"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:border focus:border-line-strong focus:bg-surface focus:px-3 focus:py-2"
        >
          {fr.skipToContent}
        </a>
        <header className="border-b border-line bg-surface">
          <div className="mx-auto flex min-h-16 max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-2 sm:px-6">
            <Link href="/" prefetch={false} className="flex shrink-0 items-center gap-2">
              <Image
                src="/brand/logo-mark.png"
                alt={fr.header.logoAlt}
                width={40}
                height={40}
                unoptimized
                priority
              />
              {/* Nom décoratif (le lien est nommé par l'alternative du symbole). SVG servi tel
                quel : il suit le thème clair ou sombre du système, comme l'app. */}
              <Image
                src="/brand/logotype.svg"
                alt=""
                width={123}
                height={22}
                unoptimized
                priority
              />
            </Link>
            <MainNav />
          </div>
        </header>
        <div id="contenu" tabIndex={-1} className="outline-none">
          {children}
        </div>
        <footer aria-label={fr.footer.label} className="mt-12 border-t border-line bg-surface">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-6 text-sm text-muted sm:px-6">
            <Link href="/methodologie" prefetch={false} className="underline hover:text-fg">
              {fr.footer.methodology}
            </Link>
            <Link href="/accessibilite" prefetch={false} className="underline hover:text-fg">
              {fr.footer.accessibility}
            </Link>
            <a href="https://github.com/gwils28/moi-electeur" className="underline hover:text-fg">
              {fr.footer.source}
            </a>
            <span className="basis-full sm:basis-auto">{fr.footer.license}</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
