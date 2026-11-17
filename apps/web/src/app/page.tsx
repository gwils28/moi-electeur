import { App } from "@/components/App";
import { loadElection } from "@/lib/load";

// Page statique : les données sont lues au build et embarquées ; la boussole fonctionne ensuite hors ligne.
export default function Home() {
  return <App data={loadElection()} />;
}
