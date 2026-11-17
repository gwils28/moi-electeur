import type { Answers, PositionLike, StatementLike } from "./types";
import { valueOf } from "./validate";

/** Seuls ces statuts sont chargés (CLAUDE.md). */
export const LOADED_STATUSES: readonly string[] = ["validated", "corrected"];

/**
 * Positions chargeables d'un candidat, par affirmation. Toute affirmation sans position
 * validated/corrected est un silence (null).
 */
export function candidateAnswers(
  positions: readonly PositionLike[],
  candidateId: string,
  statements: readonly StatementLike[],
): Answers {
  const out: Record<string, number | null> = Object.fromEntries(
    statements.map((s) => [s.id, null]),
  );
  for (const p of positions) {
    if (p.candidate_id !== candidateId || !(p.statement_id in out)) continue;
    if (!LOADED_STATUSES.includes(p.review.status)) continue;
    out[p.statement_id] = valueOf({ v: p.value }, "v");
  }
  return out;
}
