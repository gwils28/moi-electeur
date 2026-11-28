import type { Metadata } from "next";
import { Explorer } from "@/components/Explorer";
import { LegacyCompassLink } from "@/components/LegacyCompassLink";
import { fr } from "@/i18n/fr";
import { loadExplorerElections } from "@/lib/load";

export const metadata: Metadata = { title: `${fr.explorer.title} · ${fr.appName}` };

// Accueil = interrogatoire (PLAN D56). La liste des élections et des candidats est lue côté
// serveur ; seules les questions passent par /api/ask.
export default function HomePage() {
  return (
    <>
      <LegacyCompassLink />
      <Explorer elections={loadExplorerElections()} />
    </>
  );
}
