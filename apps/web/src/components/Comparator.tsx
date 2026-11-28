"use client";

import { candidateAnswers } from "@moi-electeur/engine";
import type { Measure } from "@moi-electeur/schemas-ts";
import { useEffect, useMemo, useState } from "react";
import {
  divergences,
  formatAmount,
  maskedMeasure,
  MAX_COMPARED,
  measuresFor,
  RADAR_STATUSES,
  radarGrid,
  toggleCandidate,
  type RadarStatus,
} from "@/lib/comparator";
import { electionOptions, type ElectionData } from "@/lib/data";
import { displayCandidates, nameMasker, type CandidateDisplay } from "@/lib/present";
import { sessionSeed } from "@/lib/session";
import { fr } from "@/i18n/fr";
import { ElectionPicker, PastElectionNote } from "./ElectionPicker";
import { Icon } from "./Icon";
import { ScrollRegion, STICKY_SHADOW } from "./PositionsMatrix";

const t = fr.comparator;

/** Pictogramme du radar (SVG, indépendant des polices) : la forme porte l'information et le
 * libellé texte la double (SPEC § 7) ; aucune information portée par la seule couleur. */
function StatusIcon({ status }: { status: RadarStatus }) {
  const common = { cx: 8, cy: 8, r: 6, stroke: "currentColor", strokeWidth: 1.5 };
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      {status === "chiffre" && <circle {...common} fill="currentColor" />}
      {status === "partiel" && (
        <>
          <circle {...common} fill="none" />
          <path d="M8 2 A6 6 0 0 0 8 14 Z" fill="currentColor" />
        </>
      )}
      {status === "intention" && <circle {...common} fill="none" />}
      {status === "silence" && (
        <line x1="3" y1="8" x2="13" y2="8" stroke="currentColor" strokeWidth={1.5} />
      )}
    </svg>
  );
}

function StatusMark({ status }: { status: RadarStatus }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <StatusIcon status={status} />
      <span>{t.status[status]}</span>
    </span>
  );
}

function CandidateHeader(p: { display: CandidateDisplay }) {
  return (
    <th scope="col" className="sticky top-0 z-10 border-r border-line align-bottom">
      <span className="mb-1 block"></span>
      {p.display.label}
      {p.display.party && (
        <span className="block text-xs font-normal text-muted">{p.display.party}</span>
      )}
    </th>
  );
}

function costingLabel(m: Measure): string {
  const c = m.costing;
  const parts: string[] = [t.status[c.status]];
  if (c.amount_eur !== null && c.amount_eur !== undefined) parts.push(formatAmount(c.amount_eur));
  if (c.period) parts.push(c.period);
  return parts.join(", ");
}

function MeasureDetails({ measure, display }: { measure: Measure; display: CandidateDisplay }) {
  return (
    <li className="space-y-2">
      <p className="font-semibold">{measure.title}</p>
      <p>
        <span className="badge">{costingLabel(measure)}</span>
      </p>
      <p className="text-sm">{measure.summary}</p>
      {display.hideQuotes ? (
        <p className="text-xs text-muted">{fr.quoteHidden}</p>
      ) : (
        <>
          {measure.costing.quote && (
            <blockquote className="border-l-2 border-line-strong pl-3 text-sm text-muted">
              {t.costingQuote} : « {measure.costing.quote} »
            </blockquote>
          )}
          {measure.evidence.map((ev, i) => (
            <blockquote key={i} className="border-l-2 border-line-strong pl-3 text-sm text-muted">
              « {ev.quote} » [{display.documentLabel}
              {ev.page ? `, p. ${ev.page}` : ""}]
            </blockquote>
          ))}
        </>
      )}
    </li>
  );
}

/** Comparateur face-à-face et radar des chiffrages (SPEC § 7, PLAN D34). Rien n'est envoyé. */
export function Comparator({
  elections,
  defaultId,
}: {
  elections: readonly ElectionData[];
  defaultId: string;
}) {
  const [electionId, setElectionId] = useState(defaultId);
  const data = elections.find((e) => e.config.id === electionId) ?? elections[0]!;
  const { config, statements, positions, measures } = data;
  const [seed, setSeed] = useState<number | null>(null);
  const [blind, setBlind] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [cell, setCell] = useState<{ theme: string; candidate: string } | null>(null);

  useEffect(() => setSeed(sessionSeed()), []);
  const displays = useMemo(
    () => (seed === null ? [] : displayCandidates(config.candidates, seed, blind)),
    [config, seed, blind],
  );
  // Sélection initiale : les deux premiers de l'ordre aléatoire de session.
  useEffect(() => {
    if (seed === null) return;
    setSelected(
      displayCandidates(config.candidates, seed, false)
        .slice(0, 2)
        .map((d) => d.id),
    );
    setCell(null);
  }, [config, seed]);

  const byId = useMemo(() => new Map(displays.map((d) => [d.id, d])), [displays]);
  // Mode aveugle : un titre ou un résumé de mesure peut citer un nom (texte tiré du programme).
  const mask = useMemo(
    () => (blind ? nameMasker(config.candidates, (id) => byId.get(id)?.label ?? id) : null),
    [blind, config, byId],
  );
  const cellMeasures = (candidate: string, theme: string) =>
    measuresFor(measures, candidate, theme).map((m) => maskedMeasure(m, mask));
  const compared = displays.filter((d) => selected.includes(d.id));
  const answers = useMemo(
    () =>
      Object.fromEntries(
        config.candidates.map((c) => [c.id, candidateAnswers(positions, c.id, statements)]),
      ),
    [config, positions, statements],
  );
  const diverging = divergences(
    statements,
    answers,
    compared.map((d) => d.id),
  );
  const grid = radarGrid(
    config.themes.map((th) => th.id),
    displays.map((d) => d.id),
    measures,
  );
  const themeLabel = (id: string) => config.themes.find((th) => th.id === id)?.label ?? id;
  const statementText = new Map(statements.map((s) => [s.id, s.text]));
  const options = electionOptions(elections);

  if (seed === null) return null;
  const opened = cell ? byId.get(cell.candidate) : undefined;

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="space-y-4">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{t.title}</h1>
          <p className="max-w-prose text-lg text-muted">{t.intro}</p>
        </div>
        <div className="space-y-1">
          <ElectionPicker options={options} value={config.id} onChange={setElectionId} />
          {config.fictional && <p className="text-sm font-medium">{fr.fictional}</p>}
          <PastElectionNote config={config} />
          <p className="flex items-start gap-1.5 text-sm text-muted">
            <span className="mt-0.5">
              <Icon name="info" size={16} />
            </span>
            {t.orderNote}
          </p>
        </div>
      </header>

      <section aria-labelledby="pick-title" className="panel space-y-4 text-sm">
        <fieldset className="min-w-0 space-y-2">
          <legend id="pick-title" className="mb-2 font-semibold">
            {t.pick}
          </legend>
          <div className="flex flex-wrap gap-2">
            {displays.map((d) => {
              const checked = selected.includes(d.id);
              const full = !checked && selected.length >= MAX_COMPARED;
              return (
                <label key={d.id} className="chip">
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={full}
                    onChange={() => setSelected((s) => toggleCandidate(s, d.id))}
                  />
                  {d.label}
                </label>
              );
            })}
          </div>
          <p role="status" className="text-muted">
            {selected.length < 2 ? t.pickMore : selected.length >= MAX_COMPARED ? t.pickLimit : ""}
          </p>
        </fieldset>
        <label className="chip">
          <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} />
          {fr.blind}
          {blind && <span className="font-normal">({fr.blindOn})</span>}
        </label>
      </section>

      {compared.length >= 2 && (
        <section aria-labelledby="face-title" className="space-y-4">
          <h2 id="face-title" className="text-2xl font-semibold">
            {t.faceToFace}
          </h2>
          <ScrollRegion label={t.faceCaption} hint={fr.positions.scrollHint(compared.length)}>
            <table className="data-table w-full" data-testid="face-to-face">
              <caption className="px-3 py-2 text-left font-medium">{t.faceCaption}</caption>
              <thead>
                <tr>
                  <th
                    scope="col"
                    className={`sticky left-0 top-0 z-20 border-r border-line align-bottom ${STICKY_SHADOW}`}
                  >
                    {t.theme}
                  </th>
                  {compared.map((display) => (
                    <CandidateHeader key={display.id} display={display} />
                  ))}
                </tr>
              </thead>
              <tbody>
                {config.themes.map((th) => (
                  <tr key={th.id}>
                    <th
                      scope="row"
                      className={`sticky left-0 z-10 border-r border-line bg-surface text-left ${STICKY_SHADOW}`}
                    >
                      {th.label}
                    </th>
                    {compared.map((d) => {
                      const ms = cellMeasures(d.id, th.id);
                      return (
                        <td key={d.id} className="min-w-48 border-r border-line">
                          {ms.length === 0 ? (
                            <span className="text-muted">{t.noMeasure}</span>
                          ) : (
                            <ul className="space-y-3">
                              {ms.map((m) => (
                                <li key={m.id} className="space-y-1">
                                  <span className="block">{m.title}</span>
                                  <span className="badge">{costingLabel(m)}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollRegion>

          <h3 className="text-lg font-semibold">{t.divergences}</h3>
          <p className="hint max-w-prose">{t.divergencesHelp}</p>
          {diverging.length === 0 ? (
            <p className="text-sm">{t.noDivergence}</p>
          ) : (
            <ul className="space-y-3" data-testid="divergences">
              {diverging.map((dv) => (
                <li key={dv.statementId} className="card text-sm">
                  <p>
                    <span className="text-muted">{themeLabel(dv.theme)} · </span>
                    {statementText.get(dv.statementId)}
                  </p>
                  <ul className="mt-2 flex flex-wrap gap-x-6 gap-y-1">
                    {compared.map((d) => {
                      const v = dv.values[d.id];
                      return (
                        <li key={d.id} className="flex items-center gap-1.5">
                          <span>
                            <span className="font-semibold">{d.label}</span> :{" "}
                            {v === null || v === undefined
                              ? t.silence
                              : t.positionLabels[String(v)]}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section aria-labelledby="radar-title" className="space-y-4">
        <h2 id="radar-title" className="text-2xl font-semibold">
          {t.radar}
        </h2>
        <p className="hint max-w-prose">{t.radarHelp}</p>
        {measures.length === 0 ? (
          <p className="text-sm">{t.noMeasures}</p>
        ) : (
          <>
            <ul className="card flex flex-wrap gap-x-5 gap-y-2 text-sm" aria-label={t.radar}>
              {RADAR_STATUSES.map((s) => (
                <li key={s}>
                  <StatusMark status={s} />
                </li>
              ))}
            </ul>
            <ScrollRegion label={t.radarCaption} hint={fr.positions.scrollHint(displays.length)}>
              <table className="data-table" data-testid="radar">
                <caption className="px-3 py-2 text-left font-medium">{t.radarCaption}</caption>
                <thead>
                  <tr>
                    <th
                      scope="col"
                      className={`sticky left-0 top-0 z-20 border-r border-line align-bottom ${STICKY_SHADOW}`}
                    >
                      {t.theme}
                    </th>
                    {displays.map((d) => (
                      <th
                        key={d.id}
                        scope="col"
                        className="sticky top-0 z-10 border-r border-line align-bottom"
                      >
                        <span className="mb-1 block"></span>
                        {d.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {config.themes.map((th) => (
                    <tr key={th.id}>
                      <th
                        scope="row"
                        className={`sticky left-0 z-10 border-r border-line bg-surface text-left ${STICKY_SHADOW}`}
                      >
                        {th.label}
                      </th>
                      {displays.map((d) => {
                        const status = grid[th.id]![d.id]!;
                        const open = cell?.theme === th.id && cell.candidate === d.id;
                        return (
                          <td key={d.id} className="border-r border-line p-1">
                            <button
                              type="button"
                              className={`w-full rounded-md px-1.5 py-1.5 text-left underline-offset-2 hover:underline ${
                                open ? "bg-surface outline outline-2 outline-[var(--fg)]" : ""
                              }`}
                              aria-expanded={open}
                              aria-controls="radar-details"
                              aria-label={t.cellLabel(d.label, th.label, t.status[status])}
                              onClick={() =>
                                setCell(open ? null : { theme: th.id, candidate: d.id })
                              }
                            >
                              <StatusMark status={status} />
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollRegion>
          </>
        )}
        <div id="radar-details" aria-live="polite">
          {cell && opened && (
            <section className="card" data-testid="radar-details">
              <h3 className="text-lg font-semibold">
                {t.details(opened.label, themeLabel(cell.theme))}
              </h3>
              {cellMeasures(cell.candidate, cell.theme).length === 0 ? (
                <p className="mt-2 text-sm">{t.noMeasure}</p>
              ) : (
                <ul className="mt-3 space-y-4">
                  {cellMeasures(cell.candidate, cell.theme).map((m) => (
                    <MeasureDetails key={m.id} measure={m} display={opened} />
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
