import fc from "fast-check";
import type { Answers, StatementLike } from "../src/types";

export const THEMES = ["eco", "soc", "eur"] as const;

/** 12 affirmations : 6 par axe, sens alternés, 3 thèmes. */
export const STATEMENTS: StatementLike[] = Array.from({ length: 12 }, (_, i) => ({
  id: `s${String(i + 1).padStart(2, "0")}`,
  theme: THEMES[i % 3]!,
  axis: i < 6 ? "x" : "y",
  direction: i % 2 === 0 ? 1 : -1,
  weight_in_axis: 1,
}));

export const answerArb = fc.option(fc.integer({ min: -2, max: 2 }), { nil: null });
export const valueArb = fc.integer({ min: -2, max: 2 });

export function answersArb(statements: readonly StatementLike[] = STATEMENTS) {
  return fc.tuple(...statements.map(() => answerArb)).map((vals) => toAnswers(statements, vals));
}

export function fullAnswersArb(statements: readonly StatementLike[] = STATEMENTS) {
  return fc.tuple(...statements.map(() => valueArb)).map((vals) => toAnswers(statements, vals));
}

export const weightsArb = fc.record({
  eco: fc.constantFrom(1, 2, 3),
  soc: fc.constantFrom(1, 2, 3),
  eur: fc.constantFrom(1, 2, 3),
});

export function toAnswers(
  statements: readonly StatementLike[],
  values: readonly (number | null)[],
): Answers {
  return Object.fromEntries(statements.map((s, i) => [s.id, values[i] ?? null]));
}

export function constant(value: number | null, statements = STATEMENTS): Answers {
  return Object.fromEntries(statements.map((s) => [s.id, value]));
}

/** Valeur qui pousse vers +10 (sign = 1) ou -10 (sign = -1) sur l'axe de chaque affirmation. */
export function extreme(sign: 1 | -1, statements = STATEMENTS): Answers {
  return Object.fromEntries(statements.map((s) => [s.id, 2 * s.direction * sign]));
}

export function negate(a: Answers): Answers {
  return Object.fromEntries(Object.entries(a).map(([k, v]) => [k, v === null ? null : -v]));
}
