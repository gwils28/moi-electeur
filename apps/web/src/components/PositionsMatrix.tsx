"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { electionOptions, type ElectionData } from "@/lib/data";
import { POSITION_STEPS, positionMatrix, positionStep, type PositionCell } from "@/lib/positions";
import { displayCandidates, type CandidateDisplay } from "@/lib/present";
import { sessionSeed } from "@/lib/session";
import { fr } from "@/i18n/fr";
import { ElectionPicker, PastElectionNote } from "./ElectionPicker";
import { Icon } from "./Icon";
import { Notice } from "./Notice";

const t = fr.positions;

function fullLabel(value: number | null): string {
  return value === null ? fr.comparator.silence : fr.comparator.positionLabels[String(value)]!;
}

function shortLabel(value: number | null): string {
  return value === null ? t.silenceShort : t.short[String(value)]!;
}

/**
 * Pictogramme de position : cinq crans de -2 à +2, le cran retenu est plein et plus haut ;
 * silence = trait court. La forme double le libellé texte ; aucune couleur (ni rouge ni bleu,
 * PLAN D52).
 */
export function PositionGlyph({ value }: { value: number | null }) {
  const step = positionStep(value);
  return (
    <svg
      width="44"
      height="14"
      viewBox="0 0 44 14"
      aria-hidden="true"
      focusable="false"
      className="shrink-0"
    >
      {step === null ? (
        <line x1="15" y1="7" x2="29" y2="7" stroke="currentColor" strokeWidth={1.5} />
      ) : (
        POSITION_STEPS.map((_, i) => (
          <rect
            key={i}
            x={0.5 + i * 9}
            y={i === step ? 1 : 4}
            width={7}
            height={i === step ? 12 : 6}
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
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <PositionGlyph value={value} />
      {/* Silence (valeur la plus fréquente) en retrait pour que les positions ressortent. */}
      <span className={value === null ? "text-xs text-muted" : "font-semibold tabular-nums"}>
        {shortLabel(value)}
      </span>
    </span>
  );
}

/**
 * Région de tableau défilante (spec de design M-a) : défilement interne dans les deux sens à
 * partir de `md` (en-têtes collants), horizontal seulement en dessous (zoom 400 % : la page
 * défile). Indice texte et dégradé à droite tant qu'il reste du contenu à droite ; ombre sur la
 * colonne figée (classe `group-data-[scrolled]`) quand le tableau a défilé.
 */
export function ScrollRegion({
  label,
  hint,
  children,
}: {
  label: string;
  hint: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [edge, setEdge] = useState({ scrollable: false, left: false, right: false });
  const update = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const scrollable = el.scrollWidth > el.clientWidth + 1;
    const left = el.scrollLeft > 0;
    const right = el.scrollLeft + el.clientWidth < el.scrollWidth - 1;
    setEdge((e) =>
      e.scrollable === scrollable && e.left === left && e.right === right
        ? e
        : { scrollable, left, right },
    );
  }, []);
  useEffect(() => {
    update();
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(update);
    ro.observe(el);
    if (el.firstElementChild) ro.observe(el.firstElementChild);
    return () => ro.disconnect();
  }, [update]);

  return (
    <div className="space-y-1">
      {edge.scrollable && (
        <p className="hint flex items-center gap-1">
          <Icon name="arrow-right" size={16} />
          {hint}
        </p>
      )}
      <div className="relative">
        <div
          ref={ref}
          className="group overflow-auto rounded-lg border border-line bg-surface md:max-h-[75vh]"
          tabIndex={0}
          role="region"
          aria-label={label}
          data-scrolled={edge.left ? "" : undefined}
          onScroll={update}
        >
          {children}
        </div>
        {edge.right && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-px right-px w-8 rounded-r-lg bg-linear-to-l from-surface to-transparent"
          />
        )}
      </div>
    </div>
  );
}

/** Ombre de la colonne figée, visible seulement quand la région a défilé horizontalement. */
export const STICKY_SHADOW = "group-data-[scrolled]:shadow-[4px_0_6px_-4px_rgb(0_0_0/0.3)]";

function CandidateHeader(p: { display: CandidateDisplay }) {
  return (
    <th scope="col" className="sticky top-0 z-10 min-w-28 border-r border-line align-bottom">
      <span className="mb-1 block"></span>
      {p.display.label}
      {p.display.party && (
        <span className="block text-xs font-normal text-muted">{p.display.party}</span>
      )}
    </th>
  );
}

/** Le panneau latéral fixe s'applique à partir de `md` (48 rem), comme ses classes `md:`. */
const MD_QUERY = "(min-width: 48rem)";

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
  // Candidats masqués par l'utilisateur ; par défaut, tous sont affichés.
  const [excluded, setExcluded] = useState<ReadonlySet<string>>(new Set());
  const [open, setOpen] = useState<{ statement: string; candidate: string } | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  // Cellule qui a ouvert le détail : le focus y revient à la fermeture (M-c).
  const trigger = useRef<HTMLButtonElement | null>(null);

  useEffect(() => setSeed(sessionSeed()), []);
  useEffect(() => {
    setTheme("");
    setExcluded(new Set());
    setOpen(null);
  }, [config]);

  const closeDetails = useCallback(() => {
    setOpen(null);
    const cell = trigger.current;
    if (cell?.isConnected) cell.focus();
  }, []);

  useEffect(() => {
    if (!open) return;
    // Focus dans le détail à l'ouverture : sur « Fermer le détail » (décrit par le titre), pour
    // qu'Entrée referme et rende le focus à la cellule. Le panneau fixe (md+) n'a pas besoin
    // de défilement ; sous md, le détail est sous le tableau et le focus l'amène à l'écran.
    const wide = typeof window.matchMedia === "function" && window.matchMedia(MD_QUERY).matches;
    closeButton.current?.focus({ preventScroll: wide });
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeDetails();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, closeDetails]);

  const displays = useMemo(
    () => (seed === null ? [] : displayCandidates(config.candidates, seed, blind)),
    [config, seed, blind],
  );
  // Ordre de session conservé quelle que soit la sélection.
  const visible = useMemo(() => displays.filter((d) => !excluded.has(d.id)), [displays, excluded]);
  const groups = useMemo(
    () =>
      positionMatrix(
        config.themes,
        statements,
        positions,
        visible.map((d) => d.id),
      ),
    [config, statements, positions, visible],
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
  const openedDisplay = visible.find((d) => d.id === open?.candidate);
  const position = openedCell?.position ?? null;

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="space-y-4">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{t.title}</h1>
          <p className="max-w-prose text-lg text-muted">{t.intro}</p>
        </div>
        <Notice variant="info" title={t.methodTitle} className="max-w-prose text-sm">
          <p>
            {t.method}{" "}
            <Link href="/methodologie" prefetch={false} className="text-link underline">
              {t.methodLink}
            </Link>
          </p>
        </Notice>
        <div className="space-y-1">
          <ElectionPicker
            options={electionOptions(elections)}
            value={config.id}
            onChange={setElectionId}
          />
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

      <section className="panel space-y-4 text-sm">
        <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
          <label className="flex min-w-0 max-w-full flex-col gap-1">
            <span className="font-medium">{t.themeFilter}</span>
            <select
              className="field w-full sm:w-auto"
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
          <label className="chip">
            <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} />
            {fr.blind}
            {blind && <span className="font-normal">({fr.blindOn})</span>}
          </label>
        </div>

        <fieldset className="min-w-0 space-y-2">
          <legend className="mb-2 font-medium">{t.candidateFilter}</legend>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setExcluded(new Set())}
            >
              {t.allCandidates}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setExcluded(new Set(displays.map((d) => d.id)));
                setOpen(null);
              }}
            >
              {t.noCandidates}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {displays.map((d) => (
              <label key={d.id} className="chip">
                <input
                  type="checkbox"
                  checked={!excluded.has(d.id)}
                  onChange={(e) => {
                    const show = e.target.checked;
                    setExcluded((x) => {
                      const next = new Set(x);
                      if (show) next.delete(d.id);
                      else next.add(d.id);
                      return next;
                    });
                    if (!show && open?.candidate === d.id) setOpen(null);
                  }}
                />
                {d.label}
              </label>
            ))}
          </div>
          <p role="status" className="text-muted">
            {visible.length === 0 ? t.pickOne : t.shownCount(visible.length, displays.length)}
          </p>
        </fieldset>
      </section>

      <section aria-labelledby="legend-title" className="card text-sm">
        <h2 id="legend-title" className="font-semibold">
          {t.legend}
        </h2>
        <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
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

      {visible.length > 0 && (
        <ScrollRegion label={t.caption} hint={t.scrollHint(visible.length)}>
          <table className="data-table" data-testid="positions">
            <caption className="px-3 py-2 text-left font-medium">{t.caption}</caption>
            <thead>
              <tr>
                <th
                  scope="col"
                  className={`sticky left-0 top-0 z-20 min-w-56 border-r border-line align-bottom ${STICKY_SHADOW}`}
                >
                  {t.statement}
                </th>
                {visible.map((display) => (
                  <CandidateHeader key={display.id} display={display} />
                ))}
              </tr>
            </thead>
            {shown.map((g) => (
              <tbody key={g.theme.id}>
                <tr>
                  <th
                    scope="colgroup"
                    colSpan={visible.length + 1}
                    className="bg-surface-2 text-left text-base font-semibold"
                  >
                    {/* Intitulé du thème gardé à l'écran pendant le défilement horizontal. */}
                    <span className="sticky left-2.5">{g.theme.label}</span>
                  </th>
                </tr>
                {g.rows.map((r) => (
                  <tr key={r.statement.id}>
                    <th
                      scope="row"
                      className={`sticky left-0 z-10 border-r border-line bg-surface text-left font-normal ${STICKY_SHADOW}`}
                    >
                      {r.statement.text}
                    </th>
                    {r.cells.map((c) => {
                      const d = displays.find((x) => x.id === c.candidateId)!;
                      const isOpen =
                        open?.statement === r.statement.id && open.candidate === c.candidateId;
                      return (
                        <td key={c.candidateId} className="relative border-r border-line p-1">
                          <button
                            type="button"
                            className={`w-full rounded-md px-1.5 py-1.5 text-left underline-offset-2 hover:underline ${
                              isOpen ? "bg-surface outline outline-2 outline-[var(--fg)]" : ""
                            }`}
                            aria-expanded={isOpen}
                            aria-controls="position-details"
                            onClick={(e) => {
                              trigger.current = e.currentTarget;
                              setOpen(
                                isOpen
                                  ? null
                                  : { statement: r.statement.id, candidate: c.candidateId },
                              );
                            }}
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
        </ScrollRegion>
      )}

      {/* Détail : sous le tableau en dessous de md, panneau latéral fixe à partir de md (M-c). */}
      <div id="position-details">
        {open && openedCell && openedDisplay && openedStatement && (
          <section
            aria-labelledby="position-details-title"
            className="card space-y-3 md:fixed md:inset-y-0 md:right-0 md:z-40 md:w-[28rem] md:max-w-full md:overflow-y-auto md:rounded-none md:border-y-0 md:border-r-0 md:border-l-line-strong md:shadow-[var(--shadow-pop)]"
            data-testid="position-details"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h2 id="position-details-title" className="text-lg font-semibold">
                {t.details(openedDisplay.label)}
              </h2>
              <button
                ref={closeButton}
                type="button"
                className="btn btn-secondary btn-sm"
                aria-describedby="position-details-title"
                onClick={closeDetails}
              >
                <Icon name="x" size={16} />
                {t.close}
              </button>
            </div>
            <p>
              <span className="text-muted">{openedStatement.theme} · </span>
              {openedStatement.text}
            </p>
            <p className="flex flex-wrap items-center gap-2 font-semibold">
              <PositionGlyph value={openedCell.value} />
              {fullLabel(openedCell.value)}
            </p>
            {position && (
              <p className="text-sm text-muted">
                {t.confidence} : {t.confidenceLevels[position.confidence]}
              </p>
            )}
            {position?.review.status === "corrected" && position.proposed_value !== undefined && (
              <p className="text-sm">{t.corrected(shortLabel(position.proposed_value))}</p>
            )}
            {openedDisplay.hideQuotes ? (
              <p className="text-xs text-muted">{fr.quoteHidden}</p>
            ) : !position || position.evidence.length === 0 ? (
              <p className="text-sm">{t.noEvidence}</p>
            ) : (
              <ul className="space-y-2">
                {position.evidence.map((ev, i) => (
                  <li key={i}>
                    <blockquote className="border-l-2 border-line-strong pl-3 text-sm text-muted">
                      « {ev.quote} » [{openedDisplay.documentLabel}
                      {ev.page ? `, p. ${ev.page}` : ""}]
                    </blockquote>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </div>
    </main>
  );
}
