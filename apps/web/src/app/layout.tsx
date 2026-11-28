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
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:border focus:bg-[var(--bg)] focus:px-3 focus:py-2"
        >
          {fr.skipToContent}
        </a>
        <header className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 pt-3 sm:px-6">
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
            <Image src="/brand/logotype.svg" alt="" width={123} height={22} unoptimized priority />
          </Link>
          <MainNav />
        </header>
        <div id="contenu" tabIndex={-1} className="outline-none">
          {children}
        </div>
        <footer
          aria-label={fr.footer.label}
          className="mx-auto mt-8 flex max-w-6xl flex-wrap gap-4 border-t px-4 py-4 text-sm sm:px-6"
        >
          <Link href="/methodologie" prefetch={false} className="underline">
            {fr.footer.methodology}
          </Link>
          <Link href="/accessibilite" prefetch={false} className="underline">
            {fr.footer.accessibility}
          </Link>
          <a href="https://github.com/gwils28/moi-electeur" className="underline">
            {fr.footer.source}
          </a>
          <span>{fr.footer.license}</span>
        </footer>
      </body>
    </html>
  );
}
