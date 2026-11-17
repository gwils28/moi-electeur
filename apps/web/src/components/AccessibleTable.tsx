"use client";

import { useState } from "react";
import type { CandidateDisplay } from "@/lib/present";
import { fr } from "@/i18n/fr";

export interface Row {
  display: CandidateDisplay;
  score: number | null;
  x: number | null;
  y: number | null;
}

const fmt = (v: number | null) => (v === null ? "-" : v.toFixed(1));

/** Alternative accessible à l'échiquier : ordre aléatoire par défaut, tri seulement sur demande. */
export function AccessibleTable({
  rows,
  onSelect,
}: {
  rows: readonly Row[];
  onSelect: (id: string) => void;
}) {
  const [sorted, setSorted] = useState(false);
  const shown = sorted ? [...rows].sort((a, b) => (b.score ?? -1) - (a.score ?? -1)) : rows;
  return (
    <div className="overflow-x-auto">
      <button
        type="button"
        className="mb-2 rounded border px-2 py-1 text-sm"
        onClick={() => setSorted(!sorted)}
        aria-pressed={sorted}
      >
        {sorted ? fr.unsort : fr.sortBy}
      </button>
      <table className="w-full text-left text-sm">
        <caption className="text-left font-semibold">{fr.tableCaption}</caption>
        <thead>
          <tr>
            <th scope="col">Candidat</th>
            <th scope="col">{fr.proximity}</th>
            <th scope="col">x</th>
            <th scope="col">y</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((r) => (
            <tr key={r.display.id}>
              <th scope="row" className="font-normal">
                <button type="button" className="underline" onClick={() => onSelect(r.display.id)}>
                  {r.display.label}
                </button>
              </th>
              <td>{r.score === null ? "-" : `${Math.round(r.score)} %`}</td>
              <td>{fmt(r.x)}</td>
              <td>{fmt(r.y)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
