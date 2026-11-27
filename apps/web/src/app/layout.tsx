import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { fr } from "@/i18n/fr";
import "./globals.css";

export const metadata: Metadata = { title: fr.appName, description: fr.tagline };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <nav aria-label={fr.nav.label} className="mx-auto flex max-w-6xl gap-4 px-4 pt-3 sm:px-6">
          <Link href="/" className="underline">
            {fr.nav.compass}
          </Link>
          <Link href="/explorer" className="underline">
            {fr.nav.explorer}
          </Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
