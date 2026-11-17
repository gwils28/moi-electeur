/** Types du moteur. Sous-ensembles structurels des types générés depuis schemas/ (aucune I/O). */

/** Réponse ou position sur une affirmation : -2..+2, ou null (sans avis / silence). */
export type Answer = number | null;

/** Réponses indexées par id d'affirmation. Une clé absente équivaut à null. */
export type Answers = Readonly<Record<string, Answer>>;

/** Poids par thème (×1, ×2, ×3). Un thème absent vaut 1. */
export type ThemeWeights = Readonly<Record<string, number>>;

export type Axis = "x" | "y";

export interface StatementLike {
  readonly id: string;
  readonly theme: string;
  readonly axis: Axis;
  readonly direction: -1 | 1;
  readonly weight_in_axis: number;
}

export interface PositionLike {
  readonly candidate_id: string;
  readonly statement_id: string;
  readonly value: number | null;
  readonly review: { readonly status: string };
}

export interface PcaModelLike {
  readonly statement_ids: readonly string[];
  readonly mean: readonly number[];
  readonly components: readonly (readonly number[])[];
  readonly scale: readonly number[];
}

export interface ProximityResult {
  /** 0..100 (100 = mêmes réponses sur toutes les affirmations communes). */
  readonly score: number;
  /** |S| / nombre d'affirmations répondues par l'utilisateur, dans [0, 1]. */
  readonly coverage: number;
  /** |S| : affirmations où l'utilisateur et le candidat ont une valeur. */
  readonly n: number;
  /** Nombre d'affirmations répondues par l'utilisateur. */
  readonly answered: number;
  /** Couverture < 50 % : avertissement à afficher (SPEC § 5.2). */
  readonly lowCoverage: boolean;
}

export interface Point {
  readonly x: number | null;
  readonly y: number | null;
}

export interface PcaPoint {
  readonly x: number;
  readonly y: number;
  /** Vrai si une coordonnée a été bornée à [-10, 10] (décision D4). */
  readonly clamped: boolean;
}

export interface Comparison {
  /** |écart| <= 1 */
  readonly agreements: readonly string[];
  /** |écart| >= 3 */
  readonly disagreements: readonly string[];
  /** |écart| == 2 */
  readonly partial: readonly string[];
  /** L'utilisateur a répondu, le programme est silencieux. */
  readonly candidateSilences: readonly string[];
}

export interface AnswerState {
  readonly answers: Answers;
  readonly weights: ThemeWeights;
}

export type DecodeError = "empty" | "version" | "length" | "char";
export type DecodeResult =
  | { readonly ok: true; readonly value: AnswerState }
  | { readonly ok: false; readonly error: DecodeError };
