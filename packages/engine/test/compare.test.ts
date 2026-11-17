import { describe, expect, it } from "vitest";
import { compare, filterByTheme } from "../src/compare";
import { STATEMENTS } from "./helpers";

// SPEC § 5.4 : accords |écart| <= 1, désaccords |écart| >= 3, silences du programme.
describe("compare", () => {
  const s = STATEMENTS.slice(0, 6);
  const user = { s01: 2, s02: 2, s03: 2, s04: 2, s05: null, s06: 1 };
  const cand = { s01: 1, s02: 0, s03: -1, s04: null, s05: 2, s06: -2 };

  it("classe chaque affirmation, dans l'ordre des affirmations", () => {
    expect(compare(user, cand, s)).toEqual({
      agreements: ["s01"],
      partial: ["s02"],
      disagreements: ["s03", "s06"],
      candidateSilences: ["s04"],
    });
  });

  it("une affirmation sans réponse de l'utilisateur n'apparaît nulle part", () => {
    const r = compare(user, cand, s);
    expect(Object.values(r).flat()).not.toContain("s05");
  });
});

describe("filterByTheme", () => {
  it("ne garde que le thème demandé, ordre conservé", () => {
    expect(filterByTheme(STATEMENTS, "soc").map((x) => x.id)).toEqual(["s02", "s05", "s08", "s11"]);
  });

  it("thème inconnu : liste vide", () => {
    expect(filterByTheme(STATEMENTS, "inconnu")).toEqual([]);
  });
});
