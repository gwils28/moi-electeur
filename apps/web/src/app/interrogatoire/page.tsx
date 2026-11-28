import type { Metadata } from "next";
import { Explorer } from "@/components/Explorer";
import { fr } from "@/i18n/fr";
import { loadExplorerElections } from "@/lib/load";

export const metadata: Metadata = { title: `${fr.explorer.title} · ${fr.appName}` };

// Page statique : la liste des élections et des candidats est lue au build ; seules les
// questions passent par /api/ask.
export default function ExplorerPage() {
  return <Explorer elections={loadExplorerElections()} />;
}
