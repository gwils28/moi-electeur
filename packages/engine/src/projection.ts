import type { Answers, Axis, PcaModelLike, PcaPoint, Point, StatementLike } from "./types";
import { valueOf } from "./validate";

function axisCoordinate(values: Answers, statements: readonly StatementLike[], axis: Axis) {
  let num = 0;
  let den = 0;
  for (const s of statements) {
    if (s.axis !== axis) continue;
    const v = valueOf(values, s.id);
    if (v === null) continue;
    num += s.weight_in_axis * s.direction * v;
    den += s.weight_in_axis * 2;
  }
  return den === 0 ? null : (10 * num) / den;
}

/**
 * Mode A (SPEC § 5.3) : X = 10 · Σ w·dir·v / Σ w·2 sur les affirmations de l'axe ayant une valeur.
 * Même fonction pour l'utilisateur et les candidats ; seuls les weight_in_axis comptent (D2).
 */
export function projectA(values: Answers, statements: readonly StatementLike[]): Point {
  return { x: axisCoordinate(values, statements, "x"), y: axisCoordinate(values, statements, "y") };
}

/**
 * Mode B (SPEC § 5.3) : silences imputés à 0, centrage, projection sur les 2 composantes,
 * rescale fixé par les candidats, puis bornage à [-10, 10] signalé (D4).
 */
export function projectB(values: Answers, model: PcaModelLike): PcaPoint {
  const k = model.statement_ids.length;
  const ok =
    model.mean.length === k &&
    model.components.length === 2 &&
    model.scale.length === 2 &&
    model.components.every((c) => c.length === k);
  if (!ok) throw new RangeError("Modèle ACP incohérent (tailles des vecteurs).");
  const centered = model.statement_ids.map((id, i) => (valueOf(values, id) ?? 0) - model.mean[i]!);
  let clamped = false;
  const [x, y] = model.components.map((comp, j) => {
    const raw = comp.reduce((acc, c, i) => acc + c * centered[i]!, 0) * model.scale[j]!;
    const bounded = Math.max(-10, Math.min(10, raw));
    if (bounded !== raw) clamped = true;
    return bounded === 0 ? 0 : bounded;
  });
  return { x: x!, y: y!, clamped };
}
