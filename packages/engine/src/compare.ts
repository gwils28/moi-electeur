import type { Answers, Comparison, StatementLike } from "./types";
import { valueOf } from "./validate";

/** Accords (|écart| <= 1), écarts de 2, désaccords (>= 3) et silences du programme (SPEC § 5.4). */
export function compare(
  user: Answers,
  candidate: Answers,
  statements: readonly StatementLike[],
): Comparison {
  const agreements: string[] = [];
  const partial: string[] = [];
  const disagreements: string[] = [];
  const candidateSilences: string[] = [];
  for (const s of statements) {
    const u = valueOf(user, s.id);
    if (u === null) continue;
    const c = valueOf(candidate, s.id);
    if (c === null) candidateSilences.push(s.id);
    else {
      const gap = Math.abs(u - c);
      (gap <= 1 ? agreements : gap >= 3 ? disagreements : partial).push(s.id);
    }
  }
  return { agreements, partial, disagreements, candidateSilences };
}

export function filterByTheme<S extends StatementLike>(
  statements: readonly S[],
  theme: string,
): S[] {
  return statements.filter((s) => s.theme === theme);
}
