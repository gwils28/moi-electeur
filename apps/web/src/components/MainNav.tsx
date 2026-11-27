"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { fr } from "@/i18n/fr";

const LINKS = [
  { href: "/", label: fr.nav.compass },
  { href: "/comparateur", label: fr.nav.comparator },
  { href: "/explorer", label: fr.nav.explorer },
  { href: "/methodologie", label: fr.nav.methodology },
] as const;

/** Navigation principale ; la page courante est signalée (`aria-current`, RGAA 12). */
export function MainNav() {
  const path = usePathname();
  return (
    <nav
      aria-label={fr.nav.label}
      className="mx-auto flex max-w-6xl flex-wrap gap-4 px-4 pt-3 sm:px-6"
    >
      {LINKS.map((l) => {
        const current = l.href === "/" ? path === "/" : path.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            // Aucune requête une fois la page chargée (la boussole fonctionne hors ligne).
            prefetch={false}
            className={current ? "font-semibold underline" : "underline"}
            aria-current={current ? "page" : undefined}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
