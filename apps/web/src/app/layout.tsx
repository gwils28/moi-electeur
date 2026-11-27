import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { MainNav } from "@/components/MainNav";
import { fr } from "@/i18n/fr";
import "./globals.css";

export const metadata: Metadata = { title: fr.appName, description: fr.tagline };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <a
          href="#contenu"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:border focus:bg-[var(--bg)] focus:px-3 focus:py-2"
        >
          {fr.skipToContent}
        </a>
        <MainNav />
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
