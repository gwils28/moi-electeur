import Link from "next/link";
import { fr } from "@/i18n/fr";

/** Encart de l'accueil vers l'interrogatoire, fonction centrale de l'application (PLAN D54). */
export function AskCallout() {
  return (
    <section
      aria-labelledby="ask-callout-title"
      className="flex flex-wrap items-center justify-between gap-4 rounded-lg border-2 p-4"
    >
      <div className="max-w-2xl">
        <h2 id="ask-callout-title" className="text-xl font-semibold">
          {fr.askCallout.title}
        </h2>
        <p>{fr.askCallout.text}</p>
      </div>
      <Link
        href="/interrogatoire"
        prefetch={false}
        className="rounded-full bg-[var(--fg)] px-5 py-2 font-semibold text-[var(--bg)] hover:opacity-90"
      >
        {fr.askCallout.action}
      </Link>
    </section>
  );
}
