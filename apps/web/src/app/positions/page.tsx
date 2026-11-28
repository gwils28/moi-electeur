import type { Metadata } from "next";
import { PositionsMatrix } from "@/components/PositionsMatrix";
import { defaultElection } from "@/lib/comparator";
import { loadCompassElections, PREFERRED_ELECTION } from "@/lib/load";
import { fr } from "@/i18n/fr";

export const metadata: Metadata = { title: `${fr.positions.title} · ${fr.appName}` };

// Positions revues lues côté serveur ; aucune requête une fois la page chargée (PLAN D52).
export default function PositionsPage() {
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
  return <PositionsMatrix elections={elections} defaultId={defaultId} />;
}
