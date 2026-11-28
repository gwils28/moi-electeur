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
    <nav aria-label={fr.nav.label} className="flex flex-wrap items-center gap-1 sm:gap-2">
      {LINKS.map((l) => {
        const current = l.href === "/" ? path === "/" : path.startsWith(l.href);
        // Page courante : pilule pleine (encre). L'interrogatoire garde une forme de bouton
        // (contour) sur les autres pages, pour rester mis en avant sans passer pour la page
        // courante (spec de design G2, écart assumé à D54).
        const base = "inline-flex min-h-10 items-center rounded-full px-4 py-1.5";
        const style = current
          ? `${base} bg-accent font-semibold text-accent-fg`
          : l.featured
            ? `${base} border-2 border-fg font-semibold text-fg hover:bg-surface-2`
            : `${base} font-medium text-fg hover:bg-surface-2`;
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
