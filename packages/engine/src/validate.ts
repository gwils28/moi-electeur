import type { Answer, Answers, StatementLike, ThemeWeights } from "./types";

/** Lit une valeur (clé absente = null) et vérifie qu'elle est un entier de [-2, 2]. */
export function valueOf(answers: Answers, id: string): Answer {
  const v = answers[id] ?? null;
  if (v !== null && !(Number.isInteger(v) && v >= -2 && v <= 2)) {
    throw new RangeError(`Valeur invalide pour ${id} : ${String(v)} (attendu : entier de -2 à 2).`);
  }
  return v;
}

/** Poids d'un thème (absent = 1), strictement positif et fini. */
export function weightOf(weights: ThemeWeights, theme: string): number {
  const w = weights[theme] ?? 1;
  if (!Number.isFinite(w) || w <= 0) {
    throw new RangeError(`Poids invalide pour ${theme} : ${String(w)}.`);
  }
  return w;
}

export function checkWeights(weights: ThemeWeights, statements: readonly StatementLike[]): void {
  for (const s of statements) weightOf(weights, s.theme);
  for (const t of Object.keys(weights)) weightOf(weights, t);
}
