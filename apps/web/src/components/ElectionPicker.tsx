"use client";

import type { ElectionConfig } from "@moi-electeur/schemas-ts";
import { useEffect, useState } from "react";
import { isPastElection } from "@/lib/comparator";
import { fr } from "@/i18n/fr";

export interface ElectionOption {
  readonly id: string;
  readonly label: string;
}

/** Sélecteur d'élection (D33), affiché seulement si plusieurs élections sont publiées. */
export function ElectionPicker({
  options,
  value,
  onChange,
}: {
  options: readonly ElectionOption[];
  value: string;
  onChange: (id: string) => void;
}) {
  if (options.length < 2) return null;
  return (
    <label className="mt-2 flex flex-wrap items-center gap-2 text-sm">
      <span className="font-medium">{fr.election}</span>
      <select
        className="rounded border bg-[var(--bg)] px-2 py-1 text-[var(--fg)]"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Mention « élection passée » (date du premier tour), calculée dans le navigateur. */
export function PastElectionNote({ config }: { config: ElectionConfig }) {
  const [past, setPast] = useState(false);
  useEffect(() => setPast(isPastElection(config)), [config]);
  if (!past) return null;
  const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" }).format(
    new Date(config.date_first_round),
  );
  return <p className="mt-1 text-sm font-medium">{fr.pastElection(date)}</p>;
}
