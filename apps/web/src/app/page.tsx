import { CompassHome } from "@/components/CompassHome";
import { defaultElection } from "@/lib/comparator";
import { loadCompassElections, PREFERRED_ELECTION } from "@/lib/load";
import { fr } from "@/i18n/fr";

// Page statique : les données sont lues au build et embarquées ; la boussole fonctionne ensuite hors ligne.
export default function Home() {
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
