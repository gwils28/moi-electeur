import type { Metadata } from "next";
import { Comparator } from "@/components/Comparator";
import { defaultElection } from "@/lib/comparator";
import { loadCompassElections, PREFERRED_ELECTION } from "@/lib/load";
import { fr } from "@/i18n/fr";

export const metadata: Metadata = { title: `${fr.comparator.title} · ${fr.appName}` };

// Page statique : mesures et positions revues lues au build ; aucune requête ensuite.
export default function ComparatorPage() {
  const elections = loadCompassElections();
  const defaultId = defaultElection(
    elections.map((e) => ({ id: e.config.id, fictional: e.config.fictional })),
    PREFERRED_ELECTION,
  );
  if (defaultId === null) {
    return <main className="mx-auto max-w-6xl p-4 sm:p-6">{fr.noCompass}</main>;
  }
  return <Comparator elections={elections} defaultId={defaultId} />;
}
