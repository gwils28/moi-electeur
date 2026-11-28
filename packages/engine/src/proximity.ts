import type { Answers, ProximityResult, StatementLike, ThemeWeights } from "./types";
import { checkWeights, valueOf, weightOf } from "./validate";

/**
 * Proximité (SPEC § 5.2) : distance de Manhattan normalisée pondérée par thème, sur
 * S = affirmations où l'utilisateur et le candidat ont une valeur. null si S est vide.
 */
/**
 * Score ajusté (PLAN D59) : moyenne pondérée sur toutes les réponses de l'utilisateur, où chaque
 * affirmation commune compte pour la proximité, chaque silence du programme pour SILENCE_SCORE
 * (légère pénalité, en deçà du neutre), et PRIOR_STRENGTH affirmations fictives pour PRIOR_SCORE
 * (lissage quand l'utilisateur a peu répondu). Poids de thème ; poids 1 pour les fictives.
 */
export const PRIOR_STRENGTH = 5;
export const PRIOR_SCORE = 50;
export const SILENCE_SCORE = 40;

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
  let wSilent = 0;
  for (const s of statements) {
    const u = valueOf(user, s.id);
    const c = valueOf(candidate, s.id);
    if (u === null) continue;
    answered++;
    const w = weightOf(weights, s.theme);
    if (c === null) {
      wSilent += w;
      continue;
    }
    d += w * Math.abs(u - c);
    dMax += w * 4;
    n++;
  }
  if (n === 0) return null;
  const coverage = n / answered;
  const score = 100 * (1 - d / dMax);
  const wCommon = dMax / 4;
  const adjusted =
    (wCommon * score + wSilent * SILENCE_SCORE + PRIOR_STRENGTH * PRIOR_SCORE) /
    (wCommon + wSilent + PRIOR_STRENGTH);
  return { score, adjusted, coverage, n, answered, lowCoverage: coverage < 0.5 };
}
