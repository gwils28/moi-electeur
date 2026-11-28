import type { Position, Statement } from "@moi-electeur/schemas-ts";
import { describe, expect, it } from "vitest";
import { POSITION_STEPS, positionMatrix, positionStep } from "../src/lib/positions";

const review = { status: "validated", reviewer: "t", date: "2026-11-28" } as const;

function statement(id: string, theme: string): Statement {
  return { id, theme, text: `Affirmation ${id}.`, axis: "x", direction: 1, weight_in_axis: 1 };
}

function position(
  candidate_id: string,
  statement_id: string,
  value: number | null,
  status: string = "validated",
): Position {
  return {
    candidate_id,
    statement_id,
    value,
    confidence: "high",
    evidence: [],
    proposed_by: "t",
    review: { ...review, status },
  } as Position;
}

const statements = [
  statement("s1", "eco"),
  statement("s2", "env"),
  statement("s3", "eco"),
  statement("s4", "env"),
];
const themes = [
  { id: "env", label: "Environnement" },
  { id: "eco", label: "Économie" },
  { id: "vide", label: "Thème sans affirmation" },
];

describe("positionMatrix", () => {
  it("groupe les affirmations par thème, dans l'ordre de la config puis du fichier", () => {
    const m = positionMatrix(themes, statements, [], ["a"]);
    expect(m.map((g) => g.theme.id)).toEqual(["env", "eco"]);
    expect(m[0]!.rows.map((r) => r.statement.id)).toEqual(["s2", "s4"]);
    expect(m[1]!.rows.map((r) => r.statement.id)).toEqual(["s1", "s3"]);
  });

  it("omet les thèmes sans affirmation", () => {
    const m = positionMatrix(themes, statements, [], ["a"]);
    expect(m.find((g) => g.theme.id === "vide")).toBeUndefined();
  });

  it("une cellule par candidat demandé, dans l'ordre demandé", () => {
    const m = positionMatrix(themes, statements, [], ["b", "a"]);
    expect(m[0]!.rows[0]!.cells.map((c) => c.candidateId)).toEqual(["b", "a"]);
  });

  it("valeur et position d'origine reprises ; silence explicite (valeur nulle)", () => {
    const p = position("a", "s2", 2);
    const m = positionMatrix(themes, statements, [p, position("a", "s4", null)], ["a"]);
    expect(m[0]!.rows[0]!.cells[0]).toEqual({ candidateId: "a", value: 2, position: p });
    expect(m[0]!.rows[1]!.cells[0]!.value).toBeNull();
  });

  it("position absente = silence, sans position d'origine", () => {
    const m = positionMatrix(themes, statements, [], ["a"]);
    expect(m[0]!.rows[0]!.cells[0]).toEqual({ candidateId: "a", value: null, position: null });
  });

  it("ignore les positions ni validated ni corrected (CLAUDE.md)", () => {
    const m = positionMatrix(
      themes,
      statements,
      [
        position("a", "s2", 2, "pending"),
        position("a", "s4", -1, "rejected"),
        position("a", "s1", 1, "corrected"),
      ],
      ["a"],
    );
    expect(m[0]!.rows[0]!.cells[0]).toEqual({ candidateId: "a", value: null, position: null });
    expect(m[0]!.rows[1]!.cells[0]!.value).toBeNull();
    expect(m[1]!.rows[0]!.cells[0]!.value).toBe(1);
  });

  it("ignore une affirmation d'un thème inconnu de la config", () => {
    const m = positionMatrix(themes, [...statements, statement("s9", "autre")], [], ["a"]);
    expect(m.flatMap((g) => g.rows.map((r) => r.statement.id))).not.toContain("s9");
  });
});

describe("positionStep", () => {
  it("cinq crans de -2 à +2, silence à part", () => {
    expect(POSITION_STEPS).toEqual([-2, -1, 0, 1, 2]);
    expect(positionStep(-2)).toBe(0);
    expect(positionStep(0)).toBe(2);
    expect(positionStep(2)).toBe(4);
    expect(positionStep(null)).toBeNull();
  });

  it("valeur hors échelle : bornée (donnée altérée, jamais d'erreur à l'affichage)", () => {
    expect(positionStep(5)).toBe(4);
    expect(positionStep(-3)).toBe(0);
  });
});
