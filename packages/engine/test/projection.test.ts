import { readFileSync } from "node:fs";
import { join } from "node:path";
import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { projectA, projectB } from "../src/projection";
import type { Answers, PcaModelLike } from "../src/types";
import { STATEMENTS, answersArb, constant, extreme, fullAnswersArb, negate } from "./helpers";

// SPEC § 5.3 mode A : X = 10 · Σ w·dir·v / Σ w·2 sur les affirmations de l'axe x ayant une valeur.
// Décision D2 : seuls les weight_in_axis comptent, jamais les poids de thème.

describe("projectA : exemples", () => {
  it("tout « +2 dans le sens de l'axe » : (+10, +10)", () => {
    expect(projectA(extreme(1), STATEMENTS)).toEqual({ x: 10, y: 10 });
  });

  it("tout « -2 dans le sens de l'axe » : (-10, -10)", () => {
    expect(projectA(extreme(-1), STATEMENTS)).toEqual({ x: -10, y: -10 });
  });

  it("tout neutre (0) : (0, 0)", () => {
    expect(projectA(constant(0), STATEMENTS)).toEqual({ x: 0, y: 0 });
  });

  it("calcul à la main avec weight_in_axis", () => {
    const s = [
      { id: "a", theme: "t", axis: "x" as const, direction: 1 as const, weight_in_axis: 2 },
      { id: "b", theme: "t", axis: "x" as const, direction: -1 as const, weight_in_axis: 1 },
    ];
    // v_a = 1, v_b = -2 : Σ w·dir·v = 2·1·1 + 1·(-1)·(-2) = 4 ; Σ w·2 = 6 ; X = 40 / 6.
    expect(projectA({ a: 1, b: -2 }, s).x).toBeCloseTo((10 * 4) / 6, 10);
    expect(projectA({ a: 1, b: -2 }, s).y).toBeNull();
  });

  it("silences exclus du numérateur et du dénominateur", () => {
    const s = STATEMENTS.filter((x) => x.axis === "x");
    const a: Answers = { ...extreme(1, s), [s[1]!.id]: null };
    expect(projectA(a, s).x).toBe(10);
  });

  it("aucune valeur sur un axe : coordonnée null", () => {
    const onlyX = Object.fromEntries(STATEMENTS.map((s) => [s.id, s.axis === "x" ? 1 : null]));
    expect(projectA(onlyX, STATEMENTS).y).toBeNull();
    expect(projectA(onlyX, STATEMENTS).x).not.toBeNull();
  });

  it("valeur hors bornes : RangeError", () => {
    expect(() => projectA({ s01: -3 }, STATEMENTS)).toThrow(RangeError);
  });
});

describe("projectA : propriétés", () => {
  it("coordonnées dans [-10, 10]", () => {
    fc.assert(
      fc.property(answersArb(), (a) => {
        const p = projectA(a, STATEMENTS);
        for (const c of [p.x, p.y]) {
          if (c === null) continue;
          expect(c).toBeGreaterThanOrEqual(-10);
          expect(c).toBeLessThanOrEqual(10);
        }
      }),
    );
  });

  it("antisymétrie : v -> -v donne (x, y) -> (-x, -y)", () => {
    fc.assert(
      fc.property(fullAnswersArb(), (a) => {
        const p = projectA(a, STATEMENTS);
        const q = projectA(negate(a), STATEMENTS);
        expect(q.x).toBeCloseTo(-p.x!, 10);
        expect(q.y).toBeCloseTo(-p.y!, 10);
      }),
    );
  });

  it("invariance si tous les weight_in_axis sont multipliés par k", () => {
    fc.assert(
      fc.property(fullAnswersArb(), fc.double({ min: 0.1, max: 3, noNaN: true }), (a, k) => {
        const scaled = STATEMENTS.map((s) => ({ ...s, weight_in_axis: s.weight_in_axis * k }));
        expect(projectA(a, scaled).x).toBeCloseTo(projectA(a, STATEMENTS).x!, 9);
      }),
    );
  });
});

const toy = JSON.parse(
  readFileSync(
    join(import.meta.dirname, "..", "..", "..", "schemas", "fixtures", "pca_toy.json"),
    "utf-8",
  ),
) as {
  model: PcaModelLike;
  expected: { values: Answers; x: number; y: number; clamped: boolean }[];
};

describe("projectB (fixture partagée schemas/fixtures/pca_toy.json)", () => {
  it.each(toy.expected)("valeurs $values -> ($x, $y), borné : $clamped", (c) => {
    const p = projectB(c.values, toy.model);
    expect(p.x).toBeCloseTo(c.x, 9);
    expect(p.y).toBeCloseTo(c.y, 9);
    expect(p.clamped).toBe(c.clamped);
  });

  it("coordonnées toujours dans [-10, 10]", () => {
    const s = toy.model.statement_ids.map((id) => ({
      id,
      theme: "t",
      axis: "x" as const,
      direction: 1 as const,
      weight_in_axis: 1,
    }));
    fc.assert(
      fc.property(answersArb(s), (a) => {
        const p = projectB(a, toy.model);
        expect(Math.abs(p.x)).toBeLessThanOrEqual(10);
        expect(Math.abs(p.y)).toBeLessThanOrEqual(10);
      }),
    );
  });

  it("modèle incohérent (tailles différentes) : RangeError", () => {
    const bad = { ...toy.model, mean: [0, 0] };
    expect(() => projectB({}, bad)).toThrow(RangeError);
  });
});
