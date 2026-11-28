"use client";

import type { AskCitationEvent } from "@moi-electeur/schemas-ts";
import { Fragment, useMemo, type ReactNode } from "react";
import { fr } from "@/i18n/fr";
import { layoutAnswer, type AnswerState, type Paragraph } from "@/lib/explorer/answer";
import { citationView, type CandidateDisplay } from "@/lib/present";
import { Icon } from "./Icon";
import { Notice } from "./Notice";

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
          <ul key={`ul${out.length}`} className="list-disc space-y-1 pl-6">
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
          <Fragment key={j}>
            <a
              href={`#${anchor(x.n)}`}
              className="ml-1 inline-flex h-6 min-w-6 items-center justify-center rounded-sm border border-line-strong bg-surface-2 px-1 align-middle text-xs leading-none font-semibold text-fg no-underline hover:bg-surface"
              aria-label={fr.explorer.citation(x.n)}
              onClick={() => {
                // La liste « Passages cités » est repliée : l'ouvrir avant le saut à l'ancre.
                const details = document.getElementById(anchor(x.n))?.closest("details");
                if (details) details.open = true;
              }}
            >
              {x.n}
            </a>
            {!x.citation.verified && (
              <span aria-hidden="true" className="align-super text-xs font-semibold">
                *
              </span>
            )}
          </Fragment>
        ),
      );
      if (p.list) {
        list.push(<li key={i}>{content}</li>);
        return;
      }
      flush();
      out.push(
        p.silence ? (
          <Notice key={i} variant="info" className="text-sm">
            <p>{content}</p>
          </Notice>
        ) : (
          <p key={i}>{content}</p>
        ),
      );
    });
    flush();
    return out;
  };

  const sources = (cits: readonly { n: number; citation: AskCitationEvent }[]) =>
    cits.length === 0 ? null : (
      <details className="group text-sm">
        <summary className="btn btn-ghost btn-sm -ml-2 w-fit list-none [&::-webkit-details-marker]:hidden">
          <span className="inline-flex motion-safe:transition-transform group-open:rotate-180">
            <Icon name="chevron-down" size={16} />
          </span>
          {fr.explorer.sources} ({cits.length})
        </summary>
        <ol className="mt-2 space-y-2 border-l-2 border-line pl-3">
          {cits.map(({ n, citation }) => {
            const v = citationView(
              citation,
              citation.candidate_id ? displayOf.get(citation.candidate_id) : undefined,
              blind,
            );
            return (
              <li key={n} id={anchor(n)} className="scroll-mt-4 break-words">
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
                  <span className="badge badge-warn ml-2" title={fr.explorer.unverifiedHelp}>
                    {fr.explorer.unverified}
                  </span>
                )}
                {v.quote && <q className="mt-0.5 block text-muted italic">{v.quote}</q>}
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
        <div className="max-w-prose space-y-3">
          {paragraphs(layout.preamble)}
          {sources(citesOf(layout.preamble))}
        </div>
      )}
      {layout.sections.map((s, i) => {
        return (
          <section
            key={`${s.token}-${i}`}
            className="card min-w-0 space-y-3 break-words"
            data-testid="answer-section"
          >
            <div className="flex items-center gap-2">
              <h4 className="text-lg font-semibold">
                {s.candidateId ? labelOf(s.candidateId) : fr.explorer.unknownSource}
              </h4>
            </div>
            <div className="max-w-prose space-y-3">{paragraphs(s.paragraphs)}</div>
            {sources(citesOf(s.paragraphs))}
          </section>
        );
      })}
      {done && done.unverified_citations > 0 && (
        <p className="hint">{fr.explorer.unverifiedCount(done.unverified_citations)}</p>
      )}
      {done && done.neutrality_flags.length > 0 && (
        <Notice variant="warn" className="text-sm" data-testid="neutrality-flag">
          <p>{fr.explorer.neutralityFlag}</p>
        </Notice>
      )}
      {done?.stop_reason === "max_tokens" && <p className="hint">{fr.explorer.truncated}</p>}
    </div>
  );
}
