"use client";

import type { CandidateDisplay } from "@/lib/present";
import { fr } from "@/i18n/fr";

export interface Row {
  display: CandidateDisplay;
  /** Score ajusté (PLAN D59). */
  score: number | null;
  /** Proximité sur les seules affirmations communes. */
  common: number | null;
  /** 0..1 */
  coverage: number | null;
  x: number | null;
  y: number | null;
}

const fmt = (v: number | null) => (v === null ? "-" : v.toFixed(1));
const pct = (v: number | null) => (v === null ? "-" : `${Math.round(v)} %`);

/** Alternative accessible à l'échiquier, dans l'ordre des résultats (score ajusté, PLAN D59). */
export function AccessibleTable({
  rows,
  onSelect,
}: {
  rows: readonly Row[];
  onSelect: (id: string) => void;
}) {
  return (
    <div className="min-w-0 space-y-3">
      <div className="overflow-x-auto">
        <table className="data-table w-full">
          <caption className="mb-2 text-left font-semibold">{fr.tableCaption}</caption>
          <thead>
            <tr>
              <th scope="col">{fr.candidateCol}</th>
              <th scope="col" className="num text-right">
                {fr.proximity}
              </th>
              <th scope="col" className="num text-right">
                {fr.commonCol}
              </th>
              <th scope="col" className="num text-right">
                {fr.coverageCol}
              </th>
              <th scope="col" className="num text-right">
                x
              </th>
              <th scope="col" className="num text-right">
                y
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.display.id}>
                <th scope="row" className="font-normal">
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 text-left underline underline-offset-2"
                    onClick={() => onSelect(r.display.id)}
                  >
                    {r.display.label}
                  </button>
                </th>
                <td className="num">{pct(r.score)}</td>
                <td className="num">{pct(r.common)}</td>
                <td className="num">{pct(r.coverage === null ? null : r.coverage * 100)}</td>
                <td className="num">{fmt(r.x)}</td>
                <td className="num">{fmt(r.y)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
