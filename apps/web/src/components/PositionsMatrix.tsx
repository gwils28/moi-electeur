"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { electionOptions, type ElectionData } from "@/lib/data";
import { POSITION_STEPS, positionMatrix, positionStep, type PositionCell } from "@/lib/positions";
import { displayCandidates, type CandidateDisplay } from "@/lib/present";
import { sessionSeed } from "@/lib/session";
import { fr } from "@/i18n/fr";
import { ElectionPicker, PastElectionNote } from "./ElectionPicker";

const t = fr.positions;

function fullLabel(value: number | null): string {
  return value === null ? fr.comparator.silence : fr.comparator.positionLabels[String(value)]!;
}

function shortLabel(value: number | null): string {
  return value === null ? t.silenceShort : t.short[String(value)]!;
}

/**
 * Pictogramme de position : cinq crans de -2 à +2, le cran retenu est plein ; silence = trait.
 * La forme double le libellé texte ; aucune couleur (ni rouge ni bleu, PLAN D52).
 */
function PositionGlyph({ value }: { value: number | null }) {
  const step = positionStep(value);
  return (
    <svg width="34" height="10" viewBox="0 0 34 10" aria-hidden="true" focusable="false">
      {step === null ? (
        <line x1="2" y1="5" x2="32" y2="5" stroke="currentColor" strokeWidth={1.5} />
      ) : (
        POSITION_STEPS.map((_, i) => (
          <rect
            key={i}
            x={1 + i * 6.6}
            y={i === step ? 0.75 : 2.75}
            width={5.2}
            height={i === step ? 8.5 : 4.5}
            rx={1}
            stroke="currentColor"
            strokeWidth={1}
            fill={i === step ? "currentColor" : "none"}
          />
        ))
      )}
    </svg>
  );
}

function PositionMark({ value }: { value: number | null }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <PositionGlyph value={value} />
      <span className={value === null ? "italic" : "font-medium"}>{shortLabel(value)}</span>
    </span>
  );
}

function CandidateHeader(p: { display: CandidateDisplay }) {
  return (
    <th scope="col" className="min-w-24 border p-2 text-left align-bottom">
      {p.display.label}
      {p.display.party && <span className="block font-normal">{p.display.party}</span>}
    </th>
  );
}

/** Matrice des positions (PLAN D52) : affirmations × candidats. Rien n'est envoyé. */
export function PositionsMatrix({
  elections,
  defaultId,
}: {
  elections: readonly ElectionData[];
  defaultId: string;
}) {
  const [electionId, setElectionId] = useState(defaultId);
  const data = elections.find((e) => e.config.id === electionId) ?? elections[0]!;
  const { config, statements, positions } = data;
  const [seed, setSeed] = useState<number | null>(null);
  const [blind, setBlind] = useState(false);
  const [theme, setTheme] = useState("");
  const [open, setOpen] = useState<{ statement: string; candidate: string } | null>(null);
  const details = useRef<HTMLDivElement>(null);

  useEffect(() => setSeed(sessionSeed()), []);
  useEffect(() => {
    setTheme("");
    setOpen(null);
  }, [config]);
  useEffect(() => {
    if (open) details.current?.scrollIntoView?.({ block: "nearest" });
  }, [open]);

  const displays = useMemo(
    () => (seed === null ? [] : displayCandidates(config.candidates, seed, blind)),
    [config, seed, blind],
  );
  const groups = useMemo(
    () =>
      positionMatrix(
        config.themes,
        statements,
        positions,
        displays.map((d) => d.id),
      ),
    [config, statements, positions, displays],
  );
  const shown = theme === "" ? groups : groups.filter((g) => g.theme.id === theme);

  if (seed === null) return null;

  let openedCell: PositionCell | undefined;
  let openedStatement: { text: string; theme: string } | undefined;
  for (const g of groups) {
    for (const r of g.rows) {
      if (r.statement.id !== open?.statement) continue;
      openedStatement = { text: r.statement.text, theme: g.theme.label };
      openedCell = r.cells.find((c) => c.candidateId === open.candidate);
    }
  }
  const openedDisplay = displays.find((d) => d.id === open?.candidate);
  const position = openedCell?.position ?? null;

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="space-y-1">
        <h1 className="text-3xl font-bold">{t.title}</h1>
        <p>{t.intro}</p>
        <p className="text-sm">
          {t.method}{" "}
          <Link href="/methodologie" prefetch={false} className="underline">
            {t.methodLink}
          </Link>
        </p>
        <ElectionPicker
          options={electionOptions(elections)}
          value={config.id}
          onChange={setElectionId}
        />
        {config.fictional && <p className="text-sm font-medium">{fr.fictional}</p>}
        <PastElectionNote config={config} />
        <p className="text-sm">{t.orderNote}</p>
      </header>

      <section className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <label className="flex max-w-full flex-wrap items-center gap-2">
          <span className="font-medium">{t.themeFilter}</span>
          <select
            className="w-full min-w-0 max-w-full rounded border bg-[var(--bg)] px-2 py-1 text-[var(--fg)] sm:w-auto"
            value={theme}
            onChange={(e) => {
              setTheme(e.target.value);
              setOpen(null);
            }}
          >
            <option value="">{t.allThemes}</option>
            {groups.map((g) => (
              <option key={g.theme.id} value={g.theme.id}>
                {g.theme.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} />
          {fr.blind}
          {blind && <span className="ml-1">({fr.blindOn})</span>}
        </label>
      </section>

      <section aria-labelledby="legend-title" className="text-sm">
        <h2 id="legend-title" className="font-semibold">
          {t.legend}
        </h2>
        <ul className="mt-1 flex flex-wrap gap-x-5 gap-y-1">
          {[...POSITION_STEPS].reverse().map((v) => (
            <li key={v} className="flex items-center gap-1">
              <PositionMark value={v} />
              <span>: {fullLabel(v)}</span>
            </li>
          ))}
          <li className="flex items-center gap-1">
            <PositionMark value={null} />
            <span>: {fullLabel(null)}</span>
          </li>
        </ul>
      </section>

      <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={t.caption}>
        <table className="border-collapse text-sm" data-testid="positions">
          <caption className="mb-2 text-left">{t.caption}</caption>
          <thead>
            <tr>
              <th
                scope="col"
                className="sticky left-0 z-10 min-w-56 border bg-[var(--bg)] p-2 text-left"
              >
                {t.statement}
              </th>
              {displays.map((display) => (
                <CandidateHeader key={display.id} display={display} />
              ))}
            </tr>
          </thead>
          {shown.map((g) => (
            <tbody key={g.theme.id}>
              <tr>
                <th
                  scope="colgroup"
                  colSpan={displays.length + 1}
                  className="border bg-[var(--fg)]/5 p-2 text-left text-base font-semibold"
                >
                  {g.theme.label}
                </th>
              </tr>
              {g.rows.map((r) => (
                <tr key={r.statement.id}>
                  <th
                    scope="row"
                    className="sticky left-0 z-10 border bg-[var(--bg)] p-2 text-left align-top font-normal"
                  >
                    {r.statement.text}
                  </th>
                  {r.cells.map((c) => {
                    const d = displays.find((x) => x.id === c.candidateId)!;
                    const isOpen =
                      open?.statement === r.statement.id && open.candidate === c.candidateId;
                    return (
                      <td key={c.candidateId} className="relative border p-1 align-top">
                        <button
                          type="button"
                          className={`w-full rounded px-1 py-1 text-left underline-offset-2 hover:underline ${
                            isOpen ? "outline outline-2" : ""
                          }`}
                          aria-expanded={isOpen}
                          aria-controls="position-details"
                          onClick={() =>
                            setOpen(
                              isOpen
                                ? null
                                : { statement: r.statement.id, candidate: c.candidateId },
                            )
                          }
                        >
                          {/* Nom accessible = texte visible encadré de précisions (WCAG 2.5.3). */}
                          <span className="sr-only">{t.cellBefore(d.label)}</span>
                          <PositionMark value={c.value} />
                          <span className="sr-only">{t.cellAfter(fullLabel(c.value))}</span>
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>

      <div id="position-details" ref={details} aria-live="polite">
        {open && openedCell && openedDisplay && openedStatement && (
          <section className="space-y-2 rounded border p-3" data-testid="position-details">
            <h2 className="text-lg font-semibold">{t.details(openedDisplay.label)}</h2>
            <p>
              <span className="opacity-80">{openedStatement.theme} · </span>
              {openedStatement.text}
            </p>
            <p className="flex flex-wrap items-center gap-2 font-medium">
              <PositionGlyph value={openedCell.value} />
              {fullLabel(openedCell.value)}
            </p>
            {position && (
              <p className="text-sm">
                {t.confidence} : {t.confidenceLevels[position.confidence]}
              </p>
            )}
            {position?.review.status === "corrected" && position.proposed_value !== undefined && (
              <p className="text-sm">{t.corrected(shortLabel(position.proposed_value))}</p>
            )}
            {openedDisplay.hideQuotes ? (
              <p className="text-xs italic opacity-80">{fr.quoteHidden}</p>
            ) : !position || position.evidence.length === 0 ? (
              <p className="text-sm">{t.noEvidence}</p>
            ) : (
              <ul className="space-y-2">
                {position.evidence.map((ev, i) => (
                  <li key={i}>
                    <blockquote className="ml-3 border-l-2 pl-2 text-sm italic opacity-80">
                      « {ev.quote} » [{openedDisplay.documentLabel}
                      {ev.page ? `, p. ${ev.page}` : ""}]
                    </blockquote>
                  </li>
                ))}
              </ul>
            )}
            <button type="button" className="text-sm underline" onClick={() => setOpen(null)}>
              {t.close}
            </button>
          </section>
        )}
      </div>
    </main>
  );
}
