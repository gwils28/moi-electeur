import type { Answers, ProximityResult, StatementLike, ThemeWeights } from "./types";
import { checkWeights, valueOf, weightOf } from "./validate";

/**
 * Proximité (SPEC § 5.2) : distance de Manhattan normalisée pondérée par thème, sur
 * S = affirmations où l'utilisateur et le candidat ont une valeur. null si S est vide.
 */
export function proximity(
  user: Answers,
  candidate: Answers,
  statements: readonly StatementLike[],
  weights: ThemeWeights = {},
): ProximityResult | null {
  checkWeights(weights, statements);
  let d = 0;
  let dMax = 0;
  let n = 0;
  let answered = 0;
  for (const s of statements) {
    const u = valueOf(user, s.id);
    const c = valueOf(candidate, s.id);
    if (u === null) continue;
    answered++;
    if (c === null) continue;
    const w = weightOf(weights, s.theme);
    d += w * Math.abs(u - c);
    dMax += w * 4;
    n++;
  }
  if (n === 0) return null;
  const coverage = n / answered;
  return { score: 100 * (1 - d / dMax), coverage, n, answered, lowCoverage: coverage < 0.5 };
}
