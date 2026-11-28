"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { fr } from "@/i18n/fr";

const TABS = [
  { href: "/positions", label: fr.positionsTabs.matrix },
  { href: "/positions/comparateur", label: fr.positionsTabs.comparator },
] as const;

/**
 * Sous-onglets de Positions (PLAN D55) : liens de navigation, pas un widget `tablist` (chaque
 * vue est une page). Page courante signalée par `aria-current`, le gras et un trait épais.
 */
export function PositionsTabs() {
  const path = usePathname();
  return (
    <nav aria-label={fr.positionsTabs.label} className="flex flex-wrap gap-x-1 border-b">
      {TABS.map((tab) => {
        const current = path === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            prefetch={false}
            aria-current={current ? "page" : undefined}
            className={`-mb-px border-b-4 px-3 py-2 ${
              current ? "border-[var(--fg)] font-semibold" : "border-transparent hover:underline"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
