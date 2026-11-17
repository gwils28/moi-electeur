import { ENGINE_VERSION } from "@moi-electeur/engine";
import { fr } from "@/i18n/fr";

export default function Home() {
  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-3xl font-bold">{fr.appName}</h1>
      <p className="mt-2">{fr.tagline}</p>
      <p className="mt-4 text-sm">{fr.status}</p>
      <p className="mt-1 text-sm">{fr.privacy}</p>
      <p className="mt-6 text-xs opacity-70">Moteur v{ENGINE_VERSION}</p>
    </main>
  );
}
