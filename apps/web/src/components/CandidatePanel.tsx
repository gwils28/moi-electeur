"use client";

import { compare, type Answers } from "@moi-electeur/engine";
import type { Position, Statement } from "@moi-electeur/schemas-ts";
import { useEffect, useRef } from "react";
import type { CandidateDisplay } from "@/lib/present";
import { fr } from "@/i18n/fr";
import { Icon } from "./Icon";

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
  const root = useRef<HTMLElement>(null);
  // Le panneau suit la grille de cartes : on l'amène en haut de la vue (saut instantané, sans
  // animation, donc compatible avec la réduction des animations), puis le focus va au titre.
  useEffect(() => {
    root.current?.scrollIntoView({ block: "start" });
    heading.current?.focus({ preventScroll: true });
  }, [p.display.id]);

  const group = (title: string, ids: readonly string[], testId: string) => (
    <section className="border-t border-line pt-4" data-testid={testId}>
      <h4 className="flex flex-wrap items-center gap-2 font-semibold">
        {title} <span className="badge tabular-nums">{ids.length}</span>
      </h4>
      {ids.length === 0 ? (
        <p className="mt-1 text-sm text-muted">{fr.none}</p>
      ) : (
        <ul className="mt-2 space-y-3 text-sm">
          {ids.map((id) => (
            <li key={id}>
              <p>{byId.get(id)?.text}</p>
              {p.display.hideQuotes && (evidence.get(id) ?? []).length > 0 && (
                <p className="mt-1 ml-3 text-xs text-muted italic">{fr.quoteHidden}</p>
              )}
              {(p.display.hideQuotes ? [] : (evidence.get(id) ?? [])).map((ev, i) => (
                <blockquote
                  key={i}
                  className="mt-1 ml-3 border-l-2 border-line-strong pl-3 text-muted italic"
                >
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
      ref={root}
      aria-labelledby="panel-title"
      className="card scroll-mt-4 space-y-4"
      onKeyDown={(e) => e.key === "Escape" && p.onClose()}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-start gap-2">
          <span className="mt-1.5"></span>
          <h3 id="panel-title" ref={heading} tabIndex={-1} className="text-xl font-semibold">
            {fr.panelTitle(p.display.label)}
          </h3>
        </div>
        <button type="button" className="btn btn-secondary btn-sm shrink-0" onClick={p.onClose}>
          <Icon name="x" size={16} />
          {fr.close}
        </button>
      </div>
      {p.display.party && <p className="text-sm text-muted">{p.display.party}</p>}
      {group(fr.agreements, r.agreements, "agreements")}
      {group(fr.partial, r.partial, "partial")}
      {group(fr.disagreements, r.disagreements, "disagreements")}
      {group(fr.silences, r.candidateSilences, "silences")}
    </aside>
  );
}
