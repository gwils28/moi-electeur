"use client";

import {
  filterByTheme,
  projectA,
  projectB,
  proximity,
  type Answers,
  type ThemeWeights,
} from "@moi-electeur/engine";
import { useMemo, useRef, useState } from "react";
import type { ElectionData } from "@/lib/data";
import type { CandidateDisplay } from "@/lib/present";
import { orderByAdjusted } from "@/lib/results";
import { fr } from "@/i18n/fr";
import { AccessibleTable } from "./AccessibleTable";
import { CandidatePanel } from "./CandidatePanel";
import { Chessboard } from "./Chessboard";
import { Icon } from "./Icon";
import { ProximityDial } from "./ProximityDial";
import { WhatIf } from "./WhatIf";

interface Props {
  data: ElectionData;
  displays: readonly CandidateDisplay[]; // déjà dans l'ordre aléatoire de session
  candidateAnswers: Readonly<Record<string, Answers>>;
  answers: Answers;
  weights: ThemeWeights;
  blind: boolean;
  onBlind: (blind: boolean) => void;
  onAnswer: (id: string, value: number | null) => void;
  onWeight: (theme: string, weight: number) => void;
}

type Mode = "A" | "B";

interface Snapshot {
  user: { x: number | null; y: number | null };
  scores: Record<string, number | null>;
}

export function Results(p: Props) {
  const { config, statements, pca } = p.data;
  const [mode, setMode] = useState<Mode>("A");
  const [theme, setTheme] = useState<string>("");
  const [selected, setSelected] = useState<string | null>(null);

  const active = useMemo(
    () => (theme && mode === "A" ? filterByTheme(statements, theme) : statements),
    [statements, theme, mode],
  );

  const computed = useMemo(() => {
    const point = (a: Answers) => {
      if (mode === "A") return projectA(a, active);
      const b = projectB(a, pca);
      return { x: b.x, y: b.y, clamped: b.clamped };
    };
    const user = point(p.answers);
    // Score ajusté décroissant, égalités dans l'ordre de session (PLAN D59).
    const rows = orderByAdjusted(
      p.displays.map((d) => {
        const c = p.candidateAnswers[d.id]!;
        const prox = proximity(p.answers, c, active, p.weights);
        const pt = point(c);
        return { display: d, prox, x: pt.x, y: pt.y };
      }),
    );
    return { user, rows };
  }, [mode, active, pca, p.answers, p.weights, p.displays, p.candidateAnswers]);

  // « Et si » : on mémorise l'état précédent à chaque modification faite depuis les résultats.
  const [previous, setPrevious] = useState<Snapshot | null>(null);
  const current = useRef(computed);
  current.current = computed;
  const snapshot = (): Snapshot => ({
    user: { x: current.current.user.x, y: current.current.user.y },
    scores: Object.fromEntries(
      current.current.rows.map((r) => [r.display.id, r.prox?.adjusted ?? null]),
    ),
  });
  const whatIfAnswer = (id: string, v: number | null) => {
    setPrevious(snapshot());
    p.onAnswer(id, v);
  };
  const whatIfWeight = (t: string, w: number) => {
    setPrevious(snapshot());
    p.onWeight(t, w);
  };

  const fmtDelta = (d: number) => `${d >= 0 ? "+" : ""}${d.toFixed(1)}`;
  const axisLabels =
    mode === "A"
      ? {
          x: [config.axes.x.min_label, config.axes.x.max_label] as [string, string],
          y: [config.axes.y.min_label, config.axes.y.max_label] as [string, string],
        }
      : {
          x: ["- Composante 1", "Composante 1 +"] as [string, string],
          y: ["- Composante 2", "Composante 2 +"] as [string, string],
        };
  const stmtText = new Map(statements.map((s) => [s.id, s.text]));
  const selectedDisplay = p.displays.find((d) => d.id === selected) ?? null;
  const clamped = "clamped" in computed.user && computed.user.clamped;
  const ux = computed.user.x;
  const uy = computed.user.y;

  // Panneau : mémoriser le contrôle d'origine pour lui rendre le focus à la fermeture.
  const opener = useRef<HTMLElement | SVGElement | null>(null);
  const openPanel = (id: string) => {
    const el = document.activeElement;
    opener.current = el instanceof HTMLElement || el instanceof SVGElement ? el : null;
    setSelected(id);
  };
  const closePanel = () => {
    setSelected(null);
    opener.current?.focus();
    opener.current = null;
  };

  return (
    <section aria-labelledby="results-title" className="space-y-6">
      <h2 id="results-title" className="text-2xl font-semibold">
        {fr.results}
      </h2>

      <div className="panel flex flex-wrap items-end gap-x-6 gap-y-4">
        <fieldset className="m-0 min-w-0 border-0 p-0">
          <legend className="label">{fr.mode}</legend>
          <div className="segmented">
            {(["A", "B"] as const).map((m) => (
              <label key={m}>
                <input type="radio" name="mode" checked={mode === m} onChange={() => setMode(m)} />
                {m === "A" ? fr.modeA : fr.modeB}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="min-w-0">
          <span className="label">{fr.themeFilter}</span>
          <select
            className="field"
            value={theme}
            disabled={mode === "B"}
            onChange={(e) => setTheme(e.target.value)}
          >
            <option value="">{fr.allThemes}</option>
            {config.themes.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <div className="flex min-h-11 flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              type="checkbox"
              className="size-4"
              checked={p.blind}
              onChange={(e) => p.onBlind(e.target.checked)}
            />
            {fr.blind}
          </label>
          {p.blind && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => p.onBlind(false)}
            >
              {fr.reveal}
            </button>
          )}
        </div>
      </div>
      <div className="space-y-2 text-sm text-muted">
        <p>{fr.orderNote}</p>
        {p.blind && <p className="font-medium text-fg">{fr.blindOn}</p>}
        <p>{fr.coverageNote}</p>
      </div>
      {mode === "B" && (
        <div className="card space-y-2 text-sm" data-testid="pca-info">
          <p>
            {fr.modeBNote(
              Math.round(pca.explained_variance_ratio[0]! * 100),
              Math.round(pca.explained_variance_ratio[1]! * 100),
            )}{" "}
            {fr.modeBNoTheme}
          </p>
          {pca.top_statements.map((ids, i) => (
            <div key={i}>
              <p className="font-medium">{fr.modeBAxis(i + 1)}</p>
              <ul className="ml-5 list-disc">
                {ids.map((id) => (
                  <li key={id}>{stmtText.get(id)}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-start gap-3 text-sm text-muted">
        <ProximityDial score={60} coverage={0.7} low={false} example />
        <ProximityDial score={60} coverage={0.3} low example />
        <p>{fr.dialLegend}</p>
      </div>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="proximity-list">
        {computed.rows.map((r) => {
          const prev = previous?.scores[r.display.id];
          const delta = r.prox && prev != null ? r.prox.adjusted - prev : null;
          return (
            <li key={r.display.id} className="card flex items-start gap-4">
              <ProximityDial
                score={r.prox?.adjusted ?? null}
                coverage={r.prox?.coverage ?? null}
                low={r.prox?.lowCoverage ?? false}
                previous={prev ?? null}
              />
              <div className="min-w-0 flex-1 space-y-1">
                <button
                  type="button"
                  className="inline-flex items-center gap-2 text-left text-lg font-semibold hover:underline"
                  onClick={() => openPanel(r.display.id)}
                >
                  {r.display.label}
                  <Icon name="chevron-right" />
                </button>
                {r.display.party && <p className="text-sm text-muted">{r.display.party}</p>}
                {r.prox ? (
                  <>
                    <p className="text-sm text-muted">{fr.commonScore(Math.round(r.prox.score))}</p>
                    <p className="text-sm text-muted first-letter:uppercase" data-testid="coverage">
                      {fr.coverage(Math.round(r.prox.coverage * 100))},{" "}
                      {fr.coverageDetail(r.prox.n, r.prox.answered)}
                    </p>
                    {r.prox.lowCoverage && (
                      <>
                        <p className="badge badge-warn">
                          <Icon name="alert" size={14} />
                          {fr.lowCoverageBadge}
                        </p>
                        <p className="text-sm">{fr.lowCoverage}</p>
                      </>
                    )}
                    {delta !== null && Math.abs(delta) > 0.05 && (
                      <p className="badge tabular-nums" data-testid="delta">
                        {fr.delta(fmtDelta(delta))}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-sm">{fr.noCommon}</p>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {selectedDisplay && (
        <CandidatePanel
          display={selectedDisplay}
          user={p.answers}
          candidate={p.candidateAnswers[selectedDisplay.id]!}
          statements={active}
          positions={p.data.positions}
          onClose={closePanel}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="card space-y-2">
          <Chessboard
            config={config}
            candidates={computed.rows}
            user={{ x: ux, y: uy }}
            previousUser={previous?.user ?? null}
            axisLabels={axisLabels}
            showQuadrants={mode === "A"}
            onSelect={openPanel}
          />
          <p className="text-sm" data-testid="position-text">
            {ux !== null && uy !== null ? fr.description(ux.toFixed(1), uy.toFixed(1)) : ""}
          </p>
          {clamped && <p className="text-sm">{fr.clamped}</p>}
          {ux !== null && uy !== null && <p className="text-sm text-muted">{fr.ringsNote}</p>}
        </div>
        <AccessibleTable
          rows={computed.rows.map((r) => ({
            display: r.display,
            score: r.prox?.adjusted ?? null,
            common: r.prox?.score ?? null,
            coverage: r.prox?.coverage ?? null,
            x: r.x,
            y: r.y,
          }))}
          onSelect={openPanel}
        />
      </div>

      <WhatIf
        config={config}
        statements={statements}
        answers={p.answers}
        weights={p.weights}
        onAnswer={whatIfAnswer}
        onWeight={whatIfWeight}
      />
    </section>
  );
}
