import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { proximity } from "../src/proximity";
import { STATEMENTS, answersArb, constant, fullAnswersArb, negate, weightsArb } from "./helpers";

// SPEC § 5.2 : distance de Manhattan normalisée pondérée, sur S = affirmations où
// l'utilisateur ET le candidat ont une valeur ; couverture = |S| / affirmations répondues.

describe("proximity : exemples", () => {
  it("réponses identiques : 100", () => {
    const a = constant(1);
    expect(proximity(a, a, STATEMENTS)?.score).toBe(100);
  });

  it("extrêmes opposés partout : 0", () => {
    expect(proximity(constant(2), constant(-2), STATEMENTS)?.score).toBe(0);
  });

  it("calcul à la main avec poids", () => {
    // s01 (eco, poids 2) : |2 - 0| = 2 ; s02 (soc, poids 1) : |1 - (-1)| = 2.
    const s = STATEMENTS.slice(0, 2);
    const r = proximity({ s01: 2, s02: 1 }, { s01: 0, s02: -1 }, s, { eco: 2 });
    // d = 2*2 + 1*2 = 6 ; dmax = (2 + 1) * 4 = 12 ; score = 100 * (1 - 6/12) = 50.
    expect(r?.score).toBeCloseTo(50, 10);
    expect(r?.n).toBe(2);
  });

  it("thème absent des poids : poids 1", () => {
    const s = STATEMENTS.slice(0, 2);
    const a = proximity({ s01: 2, s02: 1 }, { s01: 0, s02: -1 }, s, {});
    const b = proximity({ s01: 2, s02: 1 }, { s01: 0, s02: -1 }, s, { eco: 1, soc: 1 });
    expect(a).toEqual(b);
  });

  it("couverture et avertissement (< 50 %)", () => {
    const user = constant(1);
    const cand = { ...constant(null), s01: 1, s02: 1, s03: 1, s04: 1, s05: 1 };
    const r = proximity(user, cand, STATEMENTS);
    expect(r?.n).toBe(5);
    expect(r?.answered).toBe(12);
    expect(r?.coverage).toBeCloseTo(5 / 12, 10);
    expect(r?.lowCoverage).toBe(true);
  });

  it("couverture à exactement 50 % : pas d'avertissement", () => {
    const cand = { ...constant(null), s01: 1, s02: 1, s03: 1, s04: 1, s05: 1, s06: 1 };
    expect(proximity(constant(1), cand, STATEMENTS)?.lowCoverage).toBe(false);
  });

  it("aucune affirmation commune : null", () => {
    expect(proximity(constant(null), constant(1), STATEMENTS)).toBeNull();
    expect(proximity(constant(1), constant(null), STATEMENTS)).toBeNull();
  });

  it("clé absente = null", () => {
    expect(proximity({ s01: 1 }, { s01: 1, s02: 2 }, STATEMENTS)?.n).toBe(1);
  });

  it("valeur hors [-2, 2] ou non entière : RangeError", () => {
    expect(() => proximity({ s01: 3 }, { s01: 1 }, STATEMENTS)).toThrow(RangeError);
    expect(() => proximity({ s01: 1 }, { s01: 0.5 }, STATEMENTS)).toThrow(RangeError);
  });

  it("poids non strictement positif ou non fini : RangeError", () => {
    expect(() => proximity(constant(1), constant(1), STATEMENTS, { eco: 0 })).toThrow(RangeError);
    expect(() => proximity(constant(1), constant(1), STATEMENTS, { eco: -1 })).toThrow(RangeError);
    expect(() => proximity(constant(1), constant(1), STATEMENTS, { eco: NaN })).toThrow(RangeError);
  });
});

describe("proximity : propriétés", () => {
  it("score dans [0, 100], couverture dans [0, 1]", () => {
    fc.assert(
      fc.property(answersArb(), answersArb(), weightsArb, (u, c, w) => {
        const r = proximity(u, c, STATEMENTS, w);
        if (r === null) return;
        expect(r.score).toBeGreaterThanOrEqual(0);
        expect(r.score).toBeLessThanOrEqual(100);
        expect(r.coverage).toBeGreaterThan(0);
        expect(r.coverage).toBeLessThanOrEqual(1);
      }),
    );
  });

  it("symétrie utilisateur / candidat (score et n)", () => {
    fc.assert(
      fc.property(answersArb(), answersArb(), weightsArb, (u, c, w) => {
        const a = proximity(u, c, STATEMENTS, w);
        const b = proximity(c, u, STATEMENTS, w);
        expect(a?.score).toBe(b?.score);
        expect(a?.n).toBe(b?.n);
      }),
    );
  });

  it("invariance par multiplication de tous les poids par k > 0", () => {
    fc.assert(
      fc.property(
        answersArb(),
        answersArb(),
        weightsArb,
        fc.double({ min: 0.1, max: 100, noNaN: true }),
        (u, c, w, k) => {
          const scaled = Object.fromEntries(Object.entries(w).map(([t, v]) => [t, v * k]));
          const a = proximity(u, c, STATEMENTS, w);
          const b = proximity(u, c, STATEMENTS, scaled);
          if (a === null) expect(b).toBeNull();
          else expect(b?.score).toBeCloseTo(a.score, 9);
        },
      ),
    );
  });

  it("réponses identiques (non vides) : toujours 100", () => {
    fc.assert(
      fc.property(fullAnswersArb(), weightsArb, (a, w) => {
        expect(proximity(a, a, STATEMENTS, w)?.score).toBe(100);
      }),
    );
  });

  it("invariance par négation des deux côtés", () => {
    fc.assert(
      fc.property(answersArb(), answersArb(), (u, c) => {
        expect(proximity(negate(u), negate(c), STATEMENTS)?.score).toBe(
          proximity(u, c, STATEMENTS)?.score,
        );
      }),
    );
  });

  it("ajouter une affirmation où l'un des deux est null ne change pas le score", () => {
    fc.assert(
      fc.property(
        fullAnswersArb(),
        fullAnswersArb(),
        fc.integer({ min: 0, max: 11 }),
        (u, c, i) => {
          const id = STATEMENTS[i]!.id;
          const base = proximity(u, c, STATEMENTS)!;
          const silenced = proximity(u, { ...c, [id]: null }, STATEMENTS)!;
          const without = proximity(
            u,
            c,
            STATEMENTS.filter((s) => s.id !== id),
          )!;
          expect(silenced.score).toBeCloseTo(without.score, 10);
          expect(silenced.n).toBe(base.n - 1);
        },
      ),
    );
  });
});
