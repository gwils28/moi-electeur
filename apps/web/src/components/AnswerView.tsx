"use client";

import type { AskCitationEvent } from "@moi-electeur/schemas-ts";
import { Fragment, useMemo, type ReactNode } from "react";
import { fr } from "@/i18n/fr";
import { layoutAnswer, type AnswerState, type Paragraph } from "@/lib/explorer/answer";
import { citationView, type CandidateDisplay } from "@/lib/present";

/**
 * Une réponse de l'explorateur : sections par candidat dans l'ordre de session, citations
 * numérotées renvoyant à la liste des passages cités de la section.
 */
export function AnswerView({
  turnId,
  state,
  streaming,
  displays,
  labelOf,
  mask,
  blind,
}: {
  turnId: number;
  state: AnswerState;
  streaming: boolean;
  displays: readonly CandidateDisplay[];
  labelOf: (id: string) => string;
  mask: ((text: string) => string) | undefined;
  blind: boolean;
}) {
  const layout = useMemo(
    () =>
      layoutAnswer(state, {
        order: displays.map((d) => d.id),
        labelOf,
        ...(mask ? { mask } : {}),
        streaming,
      }),
    [state, displays, labelOf, mask, streaming],
  );
  const displayOf = useMemo(() => new Map(displays.map((d) => [d.id, d])), [displays]);
  const anchor = (n: number) => `t${turnId}-c${n}`;

  const paragraphs = (ps: readonly Paragraph[]): ReactNode[] => {
    const out: ReactNode[] = [];
    let list: ReactNode[] = [];
    const flush = () => {
      if (list.length > 0)
        out.push(
          <ul key={`ul${out.length}`} className="list-disc pl-6">
            {list}
          </ul>,
        );
      list = [];
    };
    ps.forEach((p, i) => {
      const content = p.inlines.map((x, j) =>
        x.kind === "text" ? (
          <Fragment key={j}>{x.text}</Fragment>
        ) : (
          <sup key={j}>
            <a
              href={`#${anchor(x.n)}`}
              className="ml-0.5 underline"
              aria-label={fr.explorer.citation(x.n)}
              onClick={() => {
                // La liste « Passages cités » est repliée : l'ouvrir avant le saut à l'ancre.
                const details = document.getElementById(anchor(x.n))?.closest("details");
                if (details) details.open = true;
              }}
            >
              [{x.n}]
            </a>
            {!x.citation.verified && <span aria-hidden="true">*</span>}
          </sup>
        ),
      );
      if (p.list) {
        list.push(<li key={i}>{content}</li>);
        return;
      }
      flush();
      out.push(
        <p key={i} className={p.silence ? "italic opacity-80" : undefined}>
          {content}
        </p>,
      );
    });
    flush();
    return out;
  };

  const sources = (cits: readonly { n: number; citation: AskCitationEvent }[]) =>
    cits.length === 0 ? null : (
      <details className="text-sm">
        <summary className="cursor-pointer">
          {fr.explorer.sources} ({cits.length})
        </summary>
        <ol className="mt-1 space-y-1 pl-2">
          {cits.map(({ n, citation }) => {
            const v = citationView(
              citation,
              citation.candidate_id ? displayOf.get(citation.candidate_id) : undefined,
              blind,
            );
            return (
              <li key={n} id={anchor(n)} className="scroll-mt-4">
                <span className="font-semibold">[{n}]</span> {v.source}
                {v.page && `, ${v.page}`}
                {v.href && (
                  <>
                    {" "}
                    <a
                      href={v.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline"
                    >
                      ({fr.explorer.openSource})
                    </a>
                  </>
                )}
                {!v.verified && (
                  <span
                    className="ml-2 rounded border px-1 text-xs font-semibold"
                    title={fr.explorer.unverifiedHelp}
                  >
                    {fr.explorer.unverified}
                  </span>
                )}
                {v.quote && <q className="mt-0.5 block italic">{v.quote}</q>}
              </li>
            );
          })}
        </ol>
      </details>
    );

  const citesOf = (ps: readonly Paragraph[]) =>
    ps.flatMap((p) =>
      p.inlines.flatMap((x) => (x.kind === "cite" ? [{ n: x.n, citation: x.citation }] : [])),
    );

  const done = state.done;
  return (
    <div className="space-y-4" data-testid="answer">
      {layout.preamble.length > 0 && (
        <div className="space-y-2">
          {paragraphs(layout.preamble)}
          {sources(citesOf(layout.preamble))}
        </div>
      )}
      {layout.sections.map((s, i) => (
        <section key={`${s.token}-${i}`} className="space-y-2" data-testid="answer-section">
          <h4 className="text-lg font-semibold">
            {s.candidateId ? labelOf(s.candidateId) : fr.explorer.unknownSource}
          </h4>
          {paragraphs(s.paragraphs)}
          {sources(citesOf(s.paragraphs))}
        </section>
      ))}
      {done && done.unverified_citations > 0 && (
        <p className="text-sm">{fr.explorer.unverifiedCount(done.unverified_citations)}</p>
      )}
      {done && done.neutrality_flags.length > 0 && (
        <p className="rounded border p-2 text-sm" data-testid="neutrality-flag">
          {fr.explorer.neutralityFlag}
        </p>
      )}
      {done?.stop_reason === "max_tokens" && <p className="text-sm">{fr.explorer.truncated}</p>}
    </div>
  );
}
