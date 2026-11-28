"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { fr } from "@/i18n/fr";

// L'interrogatoire, fonction centrale et page d'accueil, vient en tête en forme de bouton (D54, D56).
const LINKS = [
  { href: "/", label: fr.nav.ask, featured: true },
  { href: "/boussole", label: fr.nav.compass, featured: false },
  { href: "/positions", label: fr.nav.positions, featured: false },
] as const;

/** Navigation principale ; la page courante est signalée (`aria-current`, RGAA 12). */
export function MainNav() {
  const path = usePathname();
  return (
    <nav aria-label={fr.nav.label} className="flex flex-wrap items-center gap-4">
      {LINKS.map((l) => {
        const current = l.href === "/" ? path === "/" : path.startsWith(l.href);
        // Bouton plein aux couleurs du texte (aucune teinte connotée) ; page courante soulignée.
        const style = l.featured
          ? `rounded-full bg-[var(--fg)] px-4 py-1.5 font-semibold text-[var(--bg)] hover:opacity-90 ${
              current ? "underline underline-offset-4" : "no-underline"
            }`
          : current
            ? "font-semibold underline"
            : "underline";
        return (
          <Link
            key={l.href}
            href={l.href}
            // Aucune requête une fois la page chargée (la boussole fonctionne hors ligne).
            prefetch={false}
            className={style}
            aria-current={current ? "page" : undefined}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
