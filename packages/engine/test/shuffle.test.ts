import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { shuffleCandidates } from "../src/shuffle";

const IDS = ["c1", "c2", "c3", "c4", "c5", "c6"];

describe("shuffleCandidates", () => {
  it("renvoie une permutation, sans muter l'entrée", () => {
    fc.assert(
      fc.property(fc.integer(), (seed) => {
        const input = [...IDS];
        const out = shuffleCandidates(input, seed);
        expect(input).toEqual(IDS);
        expect([...out].sort()).toEqual([...IDS].sort());
      }),
    );
  });

  it("déterministe pour une graine donnée", () => {
    fc.assert(
      fc.property(fc.integer(), (seed) => {
        expect(shuffleCandidates(IDS, seed)).toEqual(shuffleCandidates(IDS, seed));
      }),
    );
  });

  it("chaque candidat atteint chaque rang, sans biais grossier", () => {
    const counts = IDS.map(() => IDS.map(() => 0));
    const N = 6000;
    for (let seed = 0; seed < N; seed++) {
      shuffleCandidates(IDS, seed).forEach((id, rank) => counts[IDS.indexOf(id)]![rank]!++);
    }
    // Attendu : N / 6 = 1000 par case ; tolérance large (± 20 %).
    for (const c of counts.flat()) {
      expect(c).toBeGreaterThan(800);
      expect(c).toBeLessThan(1200);
    }
  });

  it("liste vide ou d'un élément", () => {
    expect(shuffleCandidates([], 1)).toEqual([]);
    expect(shuffleCandidates(["c1"], 1)).toEqual(["c1"]);
  });
});
