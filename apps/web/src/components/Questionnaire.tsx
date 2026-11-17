"use client";

import type { Answers, ThemeWeights } from "@moi-electeur/engine";
import type { ElectionConfig, Statement } from "@moi-electeur/schemas-ts";
import { useEffect, useRef } from "react";
import { fr } from "@/i18n/fr";

interface Props {
  config: ElectionConfig;
  statements: readonly Statement[];
  themeIndex: number;
  answers: Answers;
  weights: ThemeWeights;
  onAnswer: (id: string, value: number | null) => void;
  onWeight: (theme: string, weight: number) => void;
  onNavigate: (index: number) => void;
  onFinish: () => void;
}

/** Questionnaire groupé par thème (ordre de la config), Likert 5 niveaux + « Sans avis ». */
export function Questionnaire(p: Props) {
  const theme = p.config.themes[p.themeIndex]!;
  const items = p.statements.filter((s) => s.theme === theme.id);
  const total = p.config.themes.length;
  const answeredCount = p.statements.filter((s) => p.answers[s.id] != null).length;
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), [p.themeIndex]);
  const isLast = p.themeIndex === total - 1;

  return (
    <section aria-labelledby="theme-title" className="space-y-6">
      <div>
        <p className="text-sm">{fr.themeProgress(p.themeIndex + 1, total)}</p>
        <progress
          className="w-full"
          max={total}
          value={p.themeIndex + 1}
          aria-label={fr.themeProgress(p.themeIndex + 1, total)}
        />
        <p className="text-sm">{fr.answered(answeredCount, p.statements.length)}</p>
      </div>
      <h2 id="theme-title" ref={heading} tabIndex={-1} className="text-2xl font-semibold">
        {theme.label}
      </h2>

      <label className="block">
        <span className="mr-2">{fr.weight}</span>
        <select
          className="rounded border px-2 py-1 text-[var(--fg)] bg-[var(--bg)]"
          value={p.weights[theme.id] ?? 1}
          onChange={(e) => p.onWeight(theme.id, Number(e.target.value))}
        >
          {([1, 2, 3] as const).map((w) => (
            <option key={w} value={w}>
              {fr.weightLabels[w]}
            </option>
          ))}
        </select>
      </label>

      {items.map((s) => {
        const current = p.answers[s.id] ?? null;
        return (
          <fieldset key={s.id} className="rounded border p-4">
            <legend className="px-1 font-medium">{s.text}</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {[
                ...fr.likert.map((l) => ({ value: l.value as number | null, label: l.label })),
                { value: null, label: fr.noOpinion },
              ].map((opt) => {
                const id = `${s.id}-${opt.value ?? "na"}`;
                const checked = current === opt.value && (opt.value !== null || s.id in p.answers);
                return (
                  <label
                    key={id}
                    htmlFor={id}
                    className="flex cursor-pointer items-center gap-1 rounded border px-2 py-1 has-[:checked]:bg-[var(--fg)] has-[:checked]:text-[var(--bg)] has-[:focus-visible]:outline has-[:focus-visible]:outline-2"
                  >
                    <input
                      id={id}
                      type="radio"
                      name={s.id}
                      className="sr-only"
                      checked={checked}
                      onChange={() => p.onAnswer(s.id, opt.value)}
                    />
                    {opt.label}
                  </label>
                );
              })}
            </div>
          </fieldset>
        );
      })}

      <nav className="flex justify-between gap-2" aria-label="Navigation du questionnaire">
        <button
          type="button"
          className="rounded border px-3 py-2 disabled:opacity-40"
          disabled={p.themeIndex === 0}
          onClick={() => p.onNavigate(p.themeIndex - 1)}
        >
          {fr.previous}
        </button>
        {isLast ? (
          <button
            type="button"
            className="rounded border-2 px-3 py-2 font-semibold"
            onClick={p.onFinish}
          >
            {fr.seeResults}
          </button>
        ) : (
          <button
            type="button"
            className="rounded border-2 px-3 py-2 font-semibold"
            onClick={() => p.onNavigate(p.themeIndex + 1)}
          >
            {fr.next}
          </button>
        )}
      </nav>
    </section>
  );
}
