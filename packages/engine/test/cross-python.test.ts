import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { projectA } from "../src/projection";
import { proximity } from "../src/proximity";
import type { Answers, StatementLike } from "../src/types";

// Cohérence TS / Python : la fixture est produite par la référence Python
// (`uv run pipeline engine-fixtures`), le moteur TS doit donner les mêmes résultats.
interface Cases {
  statements: StatementLike[];
  candidates: Record<string, { answers: Answers; point: { x: number | null; y: number | null } }>;
  users: {
    answers: Answers;
    weights: Record<string, number>;
    point: { x: number | null; y: number | null };
    proximity: Record<string, unknown>;
  }[];
}

const cases = JSON.parse(
  readFileSync(
    join(import.meta.dirname, "..", "..", "..", "schemas", "fixtures", "engine_cases.json"),
    "utf-8",
  ),
) as Cases;

const close = (a: number | null, b: number | null) =>
  a === null || b === null ? expect(a).toBe(b) : expect(a).toBeCloseTo(b, 9);

describe("moteur TS = référence Python (fixture engine_cases.json)", () => {
  it.each(Object.entries(cases.candidates))("projectA du candidat %s", (_id, c) => {
    const p = projectA(c.answers, cases.statements);
    close(p.x, c.point.x);
    close(p.y, c.point.y);
  });

  it.each(cases.users.map((u, i) => [i, u] as const))(
    "utilisateur %i : point et proximités",
    (_i, u) => {
      const p = projectA(u.answers, cases.statements);
      close(p.x, u.point.x);
      close(p.y, u.point.y);
      for (const [cid, expected] of Object.entries(u.proximity)) {
        const r = proximity(u.answers, cases.candidates[cid]!.answers, cases.statements, u.weights);
        if (expected === null) expect(r).toBeNull();
        else {
          const e = expected as {
            score: number;
            coverage: number;
            n: number;
            answered: number;
            lowCoverage: boolean;
          };
          expect(r?.score).toBeCloseTo(e.score, 9);
          expect(r?.coverage).toBeCloseTo(e.coverage, 9);
          expect([r?.n, r?.answered, r?.lowCoverage]).toEqual([e.n, e.answered, e.lowCoverage]);
        }
      }
    },
  );
});
