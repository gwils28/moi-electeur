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
import { fr } from "@/i18n/fr";
import { AccessibleTable } from "./AccessibleTable";
import { CandidatePanel } from "./CandidatePanel";
import { Chessboard } from "./Chessboard";
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
    const rows = p.displays.map((d) => {
      const c = p.candidateAnswers[d.id]!;
      const prox = proximity(p.answers, c, active, p.weights);
      const pt = point(c);
      return { display: d, prox, x: pt.x, y: pt.y };
    });
    return { user, rows };
  }, [mode, active, pca, p.answers, p.weights, p.displays, p.candidateAnswers]);

  // « Et si » : on mémorise l'état précédent à chaque modification faite depuis les résultats.
  const [previous, setPrevious] = useState<Snapshot | null>(null);
  const current = useRef(computed);
  current.current = computed;
  const snapshot = (): Snapshot => ({
    user: { x: current.current.user.x, y: current.current.user.y },
    scores: Object.fromEntries(
      current.current.rows.map((r) => [r.display.id, r.prox?.score ?? null]),
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

  return (
    <section aria-labelledby="results-title" className="space-y-6">
      <h2 id="results-title" className="text-2xl font-semibold">
        {fr.results}
      </h2>
      <p className="text-sm">{fr.orderNote}</p>

      <div className="flex flex-wrap items-end gap-4">
        <fieldset>
          <legend className="text-sm font-medium">{fr.mode}</legend>
          <div className="flex gap-3">
            {(["A", "B"] as const).map((m) => (
              <label key={m} className="flex items-center gap-1">
                <input type="radio" name="mode" checked={mode === m} onChange={() => setMode(m)} />
                {m === "A" ? fr.modeA : fr.modeB}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="text-sm">
          {fr.themeFilter}{" "}
          <select
            className="rounded border bg-[var(--bg)] text-[var(--fg)]"
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
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={p.blind} onChange={(e) => p.onBlind(e.target.checked)} />
          {fr.blind}
        </label>
        {p.blind && (
          <button
            type="button"
            className="rounded border px-2 py-1"
            onClick={() => p.onBlind(false)}
          >
            {fr.reveal}
          </button>
        )}
      </div>
      {p.blind && <p className="text-sm">{fr.blindOn}</p>}
      {mode === "B" && (
        <div className="text-sm" data-testid="pca-info">
          <p>
            {fr.modeBNote(
              Math.round(pca.explained_variance_ratio[0]! * 100),
              Math.round(pca.explained_variance_ratio[1]! * 100),
            )}{" "}
            {fr.modeBNoTheme}
          </p>
          {pca.top_statements.map((ids, i) => (
            <div key={i}>
              <p>{fr.modeBAxis(i + 1)}</p>
              <ul className="ml-4 list-disc">
                {ids.map((id) => (
                  <li key={id}>{stmtText.get(id)}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      <ul className="grid gap-2 sm:grid-cols-2" data-testid="proximity-list">
        {computed.rows.map((r) => {
          const prev = previous?.scores[r.display.id];
          const delta = r.prox && prev != null ? r.prox.score - prev : null;
          return (
            <li key={r.display.id} className="rounded border p-3">
              <button
                type="button"
                className="font-semibold underline"
                onClick={() => setSelected(r.display.id)}
              >
                {r.display.label}
              </button>
              {r.prox ? (
                <>
                  <p>
                    {fr.proximity} : <strong>{Math.round(r.prox.score)} %</strong>{" "}
                    <span className="text-sm">
                      ({fr.coverage(Math.round(r.prox.coverage * 100))})
                    </span>
                  </p>
                  <meter
                    min={0}
                    max={100}
                    value={r.prox.score}
                    className="w-full"
                    aria-hidden="true"
                  />
                  {r.prox.lowCoverage && <p className="text-sm">{fr.lowCoverage}</p>}
                  {delta !== null && Math.abs(delta) > 0.05 && (
                    <p className="text-sm" data-testid="delta">
                      {fr.delta(fmtDelta(delta))}
                    </p>
                  )}
                </>
              ) : (
                <p className="text-sm">{fr.noCommon}</p>
              )}
            </li>
          );
        })}
      </ul>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div>
          <Chessboard
            config={config}
            candidates={computed.rows}
            user={{ x: ux, y: uy }}
            previousUser={previous?.user ?? null}
            axisLabels={axisLabels}
            showQuadrants={mode === "A"}
            onSelect={setSelected}
          />
          <p className="text-sm" data-testid="position-text">
            {ux !== null && uy !== null ? fr.description(ux.toFixed(1), uy.toFixed(1)) : ""}
          </p>
          {clamped && <p className="text-sm">{fr.clamped}</p>}
        </div>
        <div className="space-y-4">
          {selectedDisplay && (
            <CandidatePanel
              display={selectedDisplay}
              user={p.answers}
              candidate={p.candidateAnswers[selectedDisplay.id]!}
              statements={active}
              positions={p.data.positions}
              onClose={() => setSelected(null)}
            />
          )}
          <AccessibleTable
            rows={computed.rows.map((r) => ({
              display: r.display,
              score: r.prox?.score ?? null,
              x: r.x,
              y: r.y,
            }))}
            onSelect={setSelected}
          />
        </div>
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
