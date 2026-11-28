"use client";

import type { Answers, ThemeWeights } from "@moi-electeur/engine";
import type { ElectionConfig, Statement } from "@moi-electeur/schemas-ts";
import { useEffect, useRef } from "react";
import { fr } from "@/i18n/fr";
import { Icon } from "./Icon";

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

const OPTION =
  "relative flex min-h-11 cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent";

/**
 * Questionnaire groupé par thème (ordre de la config), Likert 5 niveaux + « Sans avis ».
 * Un seul `fieldset` par affirmation, et aucun autre sur la page (le parcours e2e s'y appuie).
 */
export function Questionnaire(p: Props) {
  const theme = p.config.themes[p.themeIndex]!;
  const items = p.statements.filter((s) => s.theme === theme.id);
  const total = p.config.themes.length;
  const answeredCount = p.statements.filter((s) => p.answers[s.id] != null).length;
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), [p.themeIndex]);
  const isLast = p.themeIndex === total - 1;
  const progress = fr.themeProgress(p.themeIndex + 1, total);

  return (
    <section aria-labelledby="theme-title" className="mx-auto max-w-3xl space-y-6">
      <div className="space-y-2">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 text-sm">
          <p className="font-medium">{progress}</p>
          <p className="text-muted tabular-nums">
            {fr.answered(answeredCount, p.statements.length)}
          </p>
        </div>
        <progress className="bar" max={total} value={p.themeIndex + 1} aria-label={progress} />
      </div>
      <h2 id="theme-title" ref={heading} tabIndex={-1} className="text-2xl font-semibold">
        {theme.label}
      </h2>

      <label className="panel flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-sm font-medium">{fr.weight}</span>
        <select
          className="field"
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
        const option = (value: number | null, label: string, extra: string) => {
          const id = `${s.id}-${value ?? "na"}`;
          const checked = current === value && (value !== null || s.id in p.answers);
          const state = checked
            ? "border-accent bg-accent text-accent-fg"
            : "border-line-strong bg-surface hover:bg-surface-2";
          return (
            <label key={id} htmlFor={id} className={`${OPTION} ${state} ${extra}`}>
              <input
                id={id}
                type="radio"
                name={s.id}
                className="sr-only"
                checked={checked}
                onChange={() => p.onAnswer(s.id, value)}
              />
              {checked ? <Icon name="check" /> : <span className="w-[18px] shrink-0 sm:hidden" />}
              {label}
            </label>
          );
        };
        return (
          <div key={s.id} className="card">
            <fieldset className="m-0 min-w-0 border-0 p-0">
              <legend className="mb-3 text-lg font-medium">{s.text}</legend>
              <div
                aria-hidden="true"
                className="mb-1 hidden justify-between text-xs text-muted sm:flex"
              >
                <span>{fr.likertEnds.min}</span>
                <span>{fr.likertEnds.max}</span>
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-5">
                {fr.likert.map((l) =>
                  option(l.value, l.label, "sm:justify-center sm:px-2 sm:text-center"),
                )}
              </div>
              <div className="mt-3">
                {option(null, fr.noOpinion, "w-full border-dashed sm:w-auto sm:min-w-32")}
              </div>
            </fieldset>
          </div>
        );
      })}

      <nav
        className="sticky bottom-0 -mx-4 flex justify-between gap-2 border-t border-line bg-bg/95 px-4 py-3 sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:p-0 [@media(max-height:500px)]:static"
        aria-label="Navigation du questionnaire"
      >
        <button
          type="button"
          className="btn btn-secondary"
          disabled={p.themeIndex === 0}
          onClick={() => p.onNavigate(p.themeIndex - 1)}
        >
          {fr.previous}
        </button>
        {isLast ? (
          <button type="button" className="btn btn-primary" onClick={p.onFinish}>
            {fr.seeResults}
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => p.onNavigate(p.themeIndex + 1)}
          >
            {fr.next}
            <Icon name="arrow-right" />
          </button>
        )}
      </nav>
    </section>
  );
}
