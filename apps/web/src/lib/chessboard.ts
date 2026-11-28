/**
 * Géométrie de l'échiquier (spec de design R-c) : fonctions pures, sans React, testées à part.
 * Coordonnées en unités du viewBox SVG (y vers le bas).
 */

export interface LabelInput {
  readonly id: string;
  /** Position du marqueur dans le viewBox. */
  readonly px: number;
  readonly py: number;
  /** Côté de l'étiquette : à droite du marqueur, ou à gauche (points proches du bord droit). */
  readonly side: "left" | "right";
}

export interface LabelPlacement {
  readonly id: string;
  readonly x: number;
  readonly y: number;
  readonly anchor: "start" | "end";
  /** Trait de rappel du marqueur vers l'étiquette, quand celle-ci a été déplacée. */
  readonly leader: { x1: number; y1: number; x2: number; y2: number } | null;
}

export const LABEL_GAP = 13;
const LABEL_DX = 12;
const BASELINE = 4;
const LEADER_THRESHOLD = 4;

/**
 * Évitement glouton des collisions d'étiquettes : par côté, les étiquettes sont prises de haut en
 * bas et repoussées vers le bas pour garder un écart vertical minimal de `gap`. Une étiquette
 * déplacée de plus de 4 unités reçoit un trait de rappel. Le résultat suit l'ordre d'entrée.
 */
export function layoutLabels(
  points: readonly LabelInput[],
  gap: number = LABEL_GAP,
): LabelPlacement[] {
  const placed = new Map<string, LabelPlacement>();
  for (const side of ["left", "right"] as const) {
    const group = points
      .filter((p) => p.side === side)
      .sort((a, b) => a.py - b.py || a.px - b.px || a.id.localeCompare(b.id));
    let last = -Infinity;
    for (const p of group) {
      const natural = p.py + BASELINE;
      const y = Math.max(natural, last + gap);
      last = y;
      const x = side === "right" ? p.px + LABEL_DX : p.px - LABEL_DX;
      const moved = y - natural > LEADER_THRESHOLD;
      placed.set(p.id, {
        id: p.id,
        x,
        y,
        anchor: side === "right" ? "start" : "end",
        leader: moved
          ? { x1: p.px, y1: p.py, x2: side === "right" ? x - 2 : x + 2, y2: y - BASELINE }
          : null,
      });
    }
  }
  return points.map((p) => placed.get(p.id)!);
}

/**
 * Coupe un libellé d'axe en lignes d'au plus `max` caractères (mots entiers ; un « / » reste
 * accroché au mot qui le précède). Un mot plus long que `max` occupe sa propre ligne.
 */
export function wrapLabel(text: string, max: number): string[] {
  const words: string[] = [];
  for (const w of text.split(/\s+/).filter(Boolean)) {
    if (w === "/" && words.length > 0) words[words.length - 1] += " /";
    else words.push(w);
  }
  const lines: string[] = [];
  for (const w of words) {
    const cur = lines[lines.length - 1];
    if (cur !== undefined && cur.length + 1 + w.length <= max)
      lines[lines.length - 1] = `${cur} ${w}`;
    else lines.push(w);
  }
  return lines;
}
