import { describe, expect, it } from "vitest";
import { candidateAnswers } from "../src/positions";
import { STATEMENTS } from "./helpers";

// Le front ne charge que validated / corrected (CLAUDE.md). Un couple sans position
// chargeable est traité comme un silence (notes d'implémentation M0).
const s = STATEMENTS.slice(0, 5);
const review = (status: string) => ({ status });
const positions = [
  { candidate_id: "c1", statement_id: "s01", value: 2, review: review("validated") },
  { candidate_id: "c1", statement_id: "s02", value: -1, review: review("corrected") },
  { candidate_id: "c1", statement_id: "s03", value: 1, review: review("rejected") },
  { candidate_id: "c1", statement_id: "s04", value: 1, review: review("pending") },
  { candidate_id: "c2", statement_id: "s05", value: 2, review: review("validated") },
];

describe("candidateAnswers", () => {
  it("ne retient que validated / corrected, le reste devient silence", () => {
    expect(candidateAnswers(positions, "c1", s)).toEqual({
      s01: 2,
      s02: -1,
      s03: null,
      s04: null,
      s05: null,
    });
  });

  it("silence explicite (value null) conservé", () => {
    const p = [
      { candidate_id: "c1", statement_id: "s01", value: null, review: review("validated") },
    ];
    expect(candidateAnswers(p, "c1", s).s01).toBeNull();
  });

  it("candidat inconnu : tout en silence", () => {
    expect(Object.values(candidateAnswers(positions, "c9", s))).toEqual([
      null,
      null,
      null,
      null,
      null,
    ]);
  });

  it("position hors bornes : RangeError", () => {
    const p = [{ candidate_id: "c1", statement_id: "s01", value: 5, review: review("validated") }];
    expect(() => candidateAnswers(p, "c1", s)).toThrow(RangeError);
  });
});
