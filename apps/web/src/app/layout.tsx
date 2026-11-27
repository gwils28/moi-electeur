import type { Metadata } from "next";
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
      </body>
    </html>
  );
}
