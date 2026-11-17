"use client";

import { compare, type Answers } from "@moi-electeur/engine";
import type { Position, Statement } from "@moi-electeur/schemas-ts";
import { useEffect, useRef } from "react";
import type { CandidateDisplay } from "@/lib/present";
import { fr } from "@/i18n/fr";

interface Props {
  display: CandidateDisplay;
  user: Answers;
  candidate: Answers;
  statements: readonly Statement[];
  positions: readonly Position[];
  onClose: () => void;
}

/** Panneau latéral : accords, écarts, désaccords, silences, avec citations (SPEC § 5.4). */
export function CandidatePanel(p: Props) {
  const r = compare(p.user, p.candidate, p.statements);
  const byId = new Map(p.statements.map((s) => [s.id, s]));
  const evidence = new Map(
    p.positions
      .filter((x) => x.candidate_id === p.display.id)
      .map((x) => [x.statement_id, x.evidence]),
  );
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), [p.display.id]);

  const group = (title: string, ids: readonly string[], testId: string) => (
    <section className="mt-4" data-testid={testId}>
      <h4 className="font-semibold">
        {title} ({ids.length})
      </h4>
      {ids.length === 0 ? (
        <p className="text-sm">{fr.none}</p>
      ) : (
        <ul className="mt-1 space-y-2 text-sm">
          {ids.map((id) => (
            <li key={id}>
              <p>{byId.get(id)?.text}</p>
              {p.display.hideQuotes && (evidence.get(id) ?? []).length > 0 && (
                <p className="ml-3 text-xs italic opacity-80">{fr.quoteHidden}</p>
              )}
              {(p.display.hideQuotes ? [] : (evidence.get(id) ?? [])).map((ev, i) => (
                <blockquote key={i} className="ml-3 border-l-2 pl-2 italic opacity-80">
                  « {ev.quote} » [{p.display.documentLabel}
                  {ev.page ? `, p. ${ev.page}` : ""}]
                </blockquote>
              ))}
            </li>
          ))}
        </ul>
      )}
    </section>
  );

  return (
    <aside
      aria-labelledby="panel-title"
      className="rounded border p-4"
      onKeyDown={(e) => e.key === "Escape" && p.onClose()}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 id="panel-title" ref={heading} tabIndex={-1} className="text-xl font-semibold">
          {fr.panelTitle(p.display.label)}
        </h3>
        <button type="button" className="rounded border px-2 py-1" onClick={p.onClose}>
          {fr.close}
        </button>
      </div>
      {p.display.party && <p className="text-sm">{p.display.party}</p>}
      {group(fr.agreements, r.agreements, "agreements")}
      {group(fr.partial, r.partial, "partial")}
      {group(fr.disagreements, r.disagreements, "disagreements")}
      {group(fr.silences, r.candidateSilences, "silences")}
    </aside>
  );
}
