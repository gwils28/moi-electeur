import type { Metadata } from "next";
import type { ReactNode } from "react";
import { fr } from "@/i18n/fr";
import "./globals.css";

export const metadata: Metadata = { title: fr.appName, description: fr.tagline };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
