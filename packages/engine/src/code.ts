import type { Answers, AnswerState, DecodeResult, StatementLike } from "./types";
import { valueOf } from "./validate";

const VERSION = "1";
const LETTERS = "abcde"; // -2..+2
const NULL_LETTER = "n";
const WEIGHTS = ["1", "2", "3"];

/** Code compact pour le fragment #r= : version, une lettre par affirmation, ".", un chiffre par thème. */
export function encodeAnswers(
  state: AnswerState,
  statements: readonly StatementLike[],
  themes: readonly string[],
): string {
  const answers = statements
    .map((s) => {
      const v = valueOf(state.answers, s.id);
      return v === null ? NULL_LETTER : LETTERS[v + 2];
    })
    .join("");
  const weights = themes
    .map((t) => {
      const w = String(state.weights[t] ?? 1);
      if (!WEIGHTS.includes(w)) throw new RangeError(`Poids hors {1, 2, 3} pour ${t} : ${w}.`);
      return w;
    })
    .join("");
  return `${VERSION}${answers}.${weights}`;
}

export function decodeAnswers(
  code: string,
  statements: readonly StatementLike[],
  themes: readonly string[],
): DecodeResult {
  if (code.length === 0) return { ok: false, error: "empty" };
  if (code[0] !== VERSION) return { ok: false, error: "version" };
  const body = code.slice(1);
  if (body.length !== statements.length + 1 + themes.length) return { ok: false, error: "length" };
  if (body[statements.length] !== ".") return { ok: false, error: "char" };
  const answers: Record<string, number | null> = {};
  for (const [i, s] of statements.entries()) {
    const ch = body[i]!;
    if (ch === NULL_LETTER) answers[s.id] = null;
    else if (LETTERS.includes(ch)) answers[s.id] = LETTERS.indexOf(ch) - 2;
    else return { ok: false, error: "char" };
  }
  const weights: Record<string, number> = {};
  for (const [i, t] of themes.entries()) {
    const ch = body[statements.length + 1 + i]!;
    if (!WEIGHTS.includes(ch)) return { ok: false, error: "char" };
    weights[t] = Number(ch);
  }
  return { ok: true, value: { answers: answers as Answers, weights } };
}
