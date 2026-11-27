import type { Answers } from "@moi-electeur/engine";
import type { Measure, Statement } from "@moi-electeur/schemas-ts";

/**
 * Comparateur face-à-face et radar des chiffrages (SPEC § 7, PLAN D34). Fonctions pures, sur
 * les seules mesures et positions chargées (validated / corrected). Aucun total, aucun
 * classement : chaque cellule décrit un programme, jamais une comparaison de valeur.
 */

export type RadarStatus = "chiffre" | "partiel" | "intention" | "silence";

export const RADAR_STATUSES: readonly RadarStatus[] = [
  "chiffre",
  "partiel",
  "intention",
  "silence",
];

export const MAX_COMPARED = 3;
export const DIVERGENCE_GAP = 3;

export function measuresFor(
  measures: readonly Measure[],
  candidateId: string,
  themeId: string,
): Measure[] {
  return measures.filter((m) => m.candidate_id === candidateId && m.theme === themeId);
}

/** Statut le plus précis des mesures du thème : chiffré, puis partiel, puis intention. */
export function radarStatus(
  measures: readonly Measure[],
  candidateId: string,
  themeId: string,
): RadarStatus {
  const statuses = new Set(
    measuresFor(measures, candidateId, themeId).map((m) => m.costing.status),
  );
  if (statuses.has("chiffre")) return "chiffre";
  if (statuses.has("partiel")) return "partiel";
  if (statuses.has("intention")) return "intention";
  return "silence";
}

export function radarGrid(
  themeIds: readonly string[],
  candidateIds: readonly string[],
  measures: readonly Measure[],
): Record<string, Record<string, RadarStatus>> {
  return Object.fromEntries(
    themeIds.map((t) => [
      t,
      Object.fromEntries(candidateIds.map((c) => [c, radarStatus(measures, c, t)])),
    ]),
  );
}

export interface Divergence {
  readonly statementId: string;
  readonly theme: string;
  /** Position de chaque candidat choisi (null : silence du programme). */
  readonly values: Readonly<Record<string, number | null>>;
}

/** Affirmations où au moins deux des candidats choisis s'écartent de `minGap` ou plus. */
export function divergences(
  statements: readonly Statement[],
  answers: Readonly<Record<string, Answers>>,
  ids: readonly string[],
  minGap: number = DIVERGENCE_GAP,
): Divergence[] {
  if (ids.length < 2) return [];
  const out: Divergence[] = [];
  for (const s of statements) {
    const values = Object.fromEntries(ids.map((id) => [id, answers[id]?.[s.id] ?? null]));
    const known = Object.values(values).filter((v): v is number => v !== null);
    if (known.length >= 2 && Math.max(...known) - Math.min(...known) >= minGap) {
      out.push({ statementId: s.id, theme: s.theme, values });
    }
  }
  return out;
}

/** Ajoute ou retire un candidat de la sélection, sans dépasser `max`. */
export function toggleCandidate(
  selected: readonly string[],
  id: string,
  max: number = MAX_COMPARED,
): string[] {
  if (selected.includes(id)) return selected.filter((x) => x !== id);
  return selected.length >= max ? [...selected] : [...selected, id];
}

const NUMBER = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

/** Montant en toutes lettres d'unité : « 10 milliards d'euros », « 200 millions d'euros ». */
export function formatAmount(eur: number): string {
  const unit = (value: number, singular: string, plural: string) =>
    `${NUMBER.format(value)} ${value >= 2 ? plural : singular} d'euros`;
  if (Math.abs(eur) >= 1e9) return unit(eur / 1e9, "milliard", "milliards");
  if (Math.abs(eur) >= 1e6) return unit(eur / 1e6, "million", "millions");
  return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(eur)} euros`;
}

/**
 * Élection affichée par défaut : celle demandée si publiée, sinon l'élection réelle la plus
 * récente (2027 avant 2022), sinon la première.
 */
export function defaultElection(
  elections: readonly {
    id: string;
    fictional?: boolean | undefined;
    date_first_round?: string | undefined;
  }[],
  preferred?: string,
): string | null {
  if (preferred && elections.some((e) => e.id === preferred)) return preferred;
  const real = elections
    .filter((e) => !e.fictional)
    .sort((a, b) => (b.date_first_round ?? "").localeCompare(a.date_first_round ?? ""));
  return (real[0] ?? elections[0])?.id ?? null;
}

/** Mode aveugle : noms masqués dans le texte libre d'une mesure (titre, résumé, période). */
export function maskedMeasure(measure: Measure, mask: ((text: string) => string) | null): Measure {
  if (!mask) return measure;
  const period = measure.costing.period;
  return {
    ...measure,
    title: mask(measure.title),
    summary: mask(measure.summary),
    costing: { ...measure.costing, ...(period ? { period: mask(period) } : {}) },
  };
}

/** Élection réelle dont le premier tour est passé (mention « élection passée »). */
export function isPastElection(
  config: { date_first_round: string; fictional?: boolean | undefined },
  today: Date = new Date(),
): boolean {
  return !config.fictional && new Date(config.date_first_round) < today;
}
