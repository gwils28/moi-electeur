import { LOADED_STATUSES } from "@moi-electeur/engine";
import type { Position, Statement } from "@moi-electeur/schemas-ts";

/** Matrice des positions (PLAN D52) : affirmations × candidats, groupées par thème. */

export interface PositionCell {
  readonly candidateId: string;
  /** -2 à +2 ; null = silence (valeur nulle revue, ou aucune position chargée). */
  readonly value: number | null;
  /** Position d'origine (citations, confiance, revue) ; null si aucune n'est chargée. */
  readonly position: Position | null;
}

export interface PositionRow {
  readonly statement: Statement;
  readonly cells: readonly PositionCell[];
}

export interface PositionGroup {
  readonly theme: { readonly id: string; readonly label: string };
  readonly rows: readonly PositionRow[];
}

/**
 * Thèmes dans l'ordre de la config, affirmations dans l'ordre du fichier, cellules dans
 * l'ordre des candidats demandé (ordre aléatoire de session). Seules les positions
 * validated / corrected sont lues (CLAUDE.md) ; une absence vaut silence, comme au comparateur.
 */
export function positionMatrix(
  themes: readonly { readonly id: string; readonly label: string }[],
  statements: readonly Statement[],
  positions: readonly Position[],
  candidateIds: readonly string[],
): PositionGroup[] {
  const byKey = new Map<string, Position>();
  for (const p of positions) {
    if (LOADED_STATUSES.includes(p.review.status)) {
      byKey.set(`${p.candidate_id}\u0000${p.statement_id}`, p);
    }
  }
  return themes
    .map((theme) => ({
      theme: { id: theme.id, label: theme.label },
      rows: statements
        .filter((s) => s.theme === theme.id)
        .map((statement) => ({
          statement,
          cells: candidateIds.map((candidateId) => {
            const position = byKey.get(`${candidateId}\u0000${statement.id}`) ?? null;
            const value = position?.value ?? null;
            return { candidateId, value, position };
          }),
        })),
    }))
    .filter((g) => g.rows.length > 0);
}

export const POSITION_STEPS = [-2, -1, 0, 1, 2] as const;

/** Cran (0 à 4) du pictogramme ; null pour un silence. Borné si la donnée sort de l'échelle. */
export function positionStep(value: number | null): number | null {
  if (value === null) return null;
  return Math.min(4, Math.max(0, Math.round(value) + 2));
}
