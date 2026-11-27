import type { Measure, Statement } from "@moi-electeur/schemas-ts";
import { describe, expect, it } from "vitest";
import {
  defaultElection,
  divergences,
  formatAmount,
  isPastElection,
  measuresFor,
  radarGrid,
  radarStatus,
  toggleCandidate,
} from "../src/lib/comparator";

const review = { status: "validated", reviewer: "t", date: "2026-11-29" } as const;

function measure(
  id: string,
  candidate_id: string,
  theme: string,
  status: "chiffre" | "partiel" | "intention",
): Measure {
  return {
    id,
    candidate_id,
    theme,
    title: `Mesure ${id}`,
    summary: "Résumé.",
    costing: {
      status,
      amount_eur: status === "chiffre" ? 1e10 : null,
      period: null,
      quote: status === "intention" ? null : "Coût.",
    },
    evidence: [],
    review,
  };
}

const MEASURES = [
  measure("m001", "a", "eco", "intention"),
  measure("m002", "a", "eco", "chiffre"),
  measure("m003", "a", "social", "partiel"),
  measure("m004", "a", "social", "intention"),
  measure("m005", "b", "eco", "intention"),
];

describe("radar des chiffrages", () => {
  it("statut le plus précis du thème : chiffré, puis partiel, puis intention, sinon silence", () => {
    expect(radarStatus(MEASURES, "a", "eco")).toBe("chiffre");
    expect(radarStatus(MEASURES, "a", "social")).toBe("partiel");
    expect(radarStatus(MEASURES, "b", "eco")).toBe("intention");
    expect(radarStatus(MEASURES, "b", "social")).toBe("silence");
  });

  it("grille thèmes × candidats", () => {
    expect(radarGrid(["eco", "social"], ["b", "a"], MEASURES)).toEqual({
      eco: { b: "intention", a: "chiffre" },
      social: { b: "silence", a: "partiel" },
    });
  });

  it("mesures d'une cellule, dans l'ordre du fichier", () => {
    expect(measuresFor(MEASURES, "a", "eco").map((m) => m.id)).toEqual(["m001", "m002"]);
    expect(measuresFor(MEASURES, "b", "social")).toEqual([]);
  });
});

const STATEMENTS: Statement[] = [
  { id: "s01", theme: "eco", text: "A", axis: "x", direction: 1, weight_in_axis: 1 },
  { id: "s02", theme: "eco", text: "B", axis: "x", direction: -1, weight_in_axis: 1 },
  { id: "s03", theme: "social", text: "C", axis: "y", direction: 1, weight_in_axis: 1 },
  { id: "s04", theme: "social", text: "D", axis: "y", direction: 1, weight_in_axis: 1 },
];

describe("divergences", () => {
  const answers = {
    a: { s01: 2, s02: 1, s03: -2, s04: null },
    b: { s01: -1, s02: 0, s03: 2, s04: 2 },
    c: { s01: 2, s02: -2, s03: null, s04: -2 },
  };

  it("affirmations où deux candidats choisis s'écartent de 3 ou plus", () => {
    const got = divergences(STATEMENTS, answers, ["a", "b"]);
    expect(got.map((d) => d.statementId)).toEqual(["s01", "s03"]);
    expect(got[0]).toEqual({ statementId: "s01", theme: "eco", values: { a: 2, b: -1 } });
  });

  it("un silence n'est pas une divergence ; à trois, une seule paire suffit", () => {
    const got = divergences(STATEMENTS, answers, ["a", "b", "c"]);
    expect(got.map((d) => d.statementId)).toEqual(["s01", "s02", "s03", "s04"]);
    expect(got[2]!.values).toEqual({ a: -2, b: 2, c: null });
  });

  it("moins de deux candidats : aucune divergence", () => {
    expect(divergences(STATEMENTS, answers, ["a"])).toEqual([]);
  });
});

describe("sélection des candidats", () => {
  it("ajoute, retire, et plafonne à trois", () => {
    expect(toggleCandidate([], "a")).toEqual(["a"]);
    expect(toggleCandidate(["a", "b"], "a")).toEqual(["b"]);
    expect(toggleCandidate(["a", "b", "c"], "d")).toEqual(["a", "b", "c"]);
    expect(toggleCandidate(["a", "b", "c"], "b")).toEqual(["a", "c"]);
  });
});

describe("montants", () => {
  const plain = (s: string) => s.replace(/[\u202f\u00a0]/g, " ");
  it("en milliards, millions ou euros, à la française", () => {
    expect(plain(formatAmount(1e10))).toBe("10 milliards d'euros");
    expect(plain(formatAmount(1.5e9))).toBe("1,5 milliard d'euros");
    expect(plain(formatAmount(2e8))).toBe("200 millions d'euros");
    expect(plain(formatAmount(1e6))).toBe("1 million d'euros");
    expect(plain(formatAmount(15000))).toBe("15 000 euros");
  });
});

describe("élection par défaut et mention d'élection passée", () => {
  const list = [
    { id: "demo-fictive", fictional: true },
    { id: "fr-presidentielle-2022", fictional: false },
  ];
  it("élection demandée si publiée, sinon la première réelle, sinon la première", () => {
    expect(defaultElection(list, "demo-fictive")).toBe("demo-fictive");
    expect(defaultElection(list, "absente")).toBe("fr-presidentielle-2022");
    expect(defaultElection(list)).toBe("fr-presidentielle-2022");
    expect(defaultElection([list[0]!])).toBe("demo-fictive");
    expect(defaultElection([])).toBeNull();
  });
  it("élection passée : premier tour antérieur à aujourd'hui", () => {
    const today = new Date("2026-11-29");
    expect(isPastElection({ date_first_round: "2022-04-10", fictional: false }, today)).toBe(true);
    expect(isPastElection({ date_first_round: "2027-04-11", fictional: false }, today)).toBe(false);
    expect(isPastElection({ date_first_round: "2022-04-10", fictional: true }, today)).toBe(false);
  });
});
