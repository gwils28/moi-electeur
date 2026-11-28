"use client";

import type { Answers, ThemeWeights } from "@moi-electeur/engine";
import type { ElectionConfig, Statement } from "@moi-electeur/schemas-ts";
import { fr } from "@/i18n/fr";

interface Props {
  config: ElectionConfig;
  statements: readonly Statement[];
  answers: Answers;
  weights: ThemeWeights;
  onAnswer: (id: string, value: number | null) => void;
  onWeight: (theme: string, weight: number) => void;
}

/** Simulateur « Et si… » (SPEC § 5.6) : réponses et poids modifiables depuis les résultats. */
export function WhatIf(p: Props) {
  return (
    <details className="card">
      <summary className="cursor-pointer text-lg font-semibold">{fr.whatIf}</summary>
      <p className="hint mt-2">{fr.whatIfHelp}</p>
      {p.config.themes.map((t) => (
        <fieldset key={t.id} className="m-0 mt-6 min-w-0 border-0 border-t border-line p-0 pt-4">
          <legend className="float-left mb-2 w-full font-semibold">{t.label}</legend>
          <label className="clear-left flex flex-wrap items-center gap-2 text-sm font-medium">
            {fr.weight}
            <select
              className="field"
              value={p.weights[t.id] ?? 1}
              onChange={(e) => p.onWeight(t.id, Number(e.target.value))}
            >
              {([1, 2, 3] as const).map((w) => (
                <option key={w} value={w}>
                  {fr.weightLabels[w]}
                </option>
              ))}
            </select>
          </label>
          {p.statements
            .filter((s) => s.theme === t.id)
            .map((s) => (
              <label
                key={s.id}
                className="mt-3 flex flex-col gap-1 text-sm sm:flex-row sm:items-center sm:justify-between sm:gap-4"
              >
                <span>{s.text}</span>
                <select
                  data-testid={`whatif-${s.id}`}
                  className="field shrink-0"
                  value={p.answers[s.id] ?? "na"}
                  onChange={(e) =>
                    p.onAnswer(s.id, e.target.value === "na" ? null : Number(e.target.value))
                  }
                >
                  {fr.likert.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                  <option value="na">{fr.noOpinion}</option>
                </select>
              </label>
            ))}
        </fieldset>
      ))}
    </details>
  );
}
