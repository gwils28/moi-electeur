import type { Metadata } from "next";
import { CompassHome } from "@/components/CompassHome";
import { defaultElection } from "@/lib/comparator";
import { loadCompassElections, PREFERRED_ELECTION } from "@/lib/load";
import { fr } from "@/i18n/fr";

export const metadata: Metadata = { title: `${fr.compass.title} · ${fr.appName}` };

// Données lues côté serveur et embarquées ; la boussole fonctionne ensuite hors ligne.
export default function CompassPage() {
  const elections = loadCompassElections();
  const defaultId = defaultElection(
    elections.map((e) => ({
      id: e.config.id,
      fictional: e.config.fictional,
      date_first_round: e.config.date_first_round,
    })),
    PREFERRED_ELECTION,
  );
  if (defaultId === null) {
    return <main className="mx-auto max-w-6xl p-4 sm:p-6">{fr.noCompass}</main>;
  }
  return <CompassHome elections={elections} defaultId={defaultId} />;
}
